"""


"""
import json
import logging
import decimal

from mitxmako.shortcuts import render_to_response

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic.base import View
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.utils.http import urlencode
from django.contrib.auth.decorators import login_required

from course_modes.models import CourseMode
from student.models import CourseEnrollment
from student.views import course_from_id
from shoppingcart.models import Order, CertificateItem
from shoppingcart.processors.CyberSource import (
    get_signed_purchase_params, get_purchase_endpoint
)
from verify_student.models import SoftwareSecurePhotoVerification
import ssencrypt

log = logging.getLogger(__name__)

class VerifyView(View):

    @method_decorator(login_required)
    def get(self, request, course_id):
        """
        """
        # If the user has already been verified within the given time period,
        # redirect straight to the payment -- no need to verify again.
        if SoftwareSecurePhotoVerification.user_has_valid_or_pending(request.user):
            return redirect(
                reverse('verify_student_verified',
                        kwargs={'course_id': course_id}))
        elif CourseEnrollment.enrollment_mode_for_user(request.user, course_id) == 'verified':
            return redirect(reverse('dashboard'))
        else:
            # If they haven't completed a verification attempt, we have to
            # restart with a new one. We can't reuse an older one because we
            # won't be able to show them their encrypted photo_id -- it's easier
            # bookkeeping-wise just to start over.
            progress_state = "start"

        verify_mode = CourseMode.mode_for_course(course_id, "verified")
        if course_id in request.session.get("donation_for_course", {}):
            chosen_price = request.session["donation_for_course"][course_id]
        else:
            chosen_price = verify_mode.min_price

        course = course_from_id(course_id)
        context = {
            "progress_state": progress_state,
            "user_full_name": request.user.profile.name,
            "course_id": course_id,
            "course_name": course.display_name_with_default,
            "course_org" : course.display_org_with_default,
            "course_num" : course.display_number_with_default,
            "purchase_endpoint": get_purchase_endpoint(),
            "suggested_prices": [
                decimal.Decimal(price)
                for price in verify_mode.suggested_prices.split(",")
            ],
            "currency": verify_mode.currency.upper(),
            "chosen_price": chosen_price,
            "min_price": verify_mode.min_price,
        }

        return render_to_response('verify_student/photo_verification.html', context)


class VerifiedView(View):
    """
    View that gets shown once the user has already gone through the
    verification flow
    """
    @method_decorator(login_required)
    def get(self, request, course_id):
        """
        Handle the case where we have a get request
        """
        if CourseEnrollment.enrollment_mode_for_user(request.user, course_id) == 'verified':
            return redirect(reverse('dashboard'))
        verify_mode = CourseMode.mode_for_course(course_id, "verified")
        if course_id in request.session.get("donation_for_course", {}):
            chosen_price = request.session["donation_for_course"][course_id]
        else:
            chosen_price = verify_mode.min_price.format("{:g}")

        course = course_from_id(course_id)
        context = {
            "course_id": course_id,
            "course_name": course.display_name_with_default,
            "course_org" : course.display_org_with_default,
            "course_num" : course.display_number_with_default,
            "purchase_endpoint": get_purchase_endpoint(),
            "currency": verify_mode.currency.upper(),
            "chosen_price": chosen_price,
        }
        return render_to_response('verify_student/verified.html', context)


@login_required
def create_order(request):
    """
    Submit PhotoVerification and create a new Order for this verified cert
    """
    if not SoftwareSecurePhotoVerification.user_has_valid_or_pending(request.user):
        attempt = SoftwareSecurePhotoVerification(user=request.user)
        b64_face_image = request.POST['face_image'].split(",")[1]
        b64_photo_id_image = request.POST['photo_id_image'].split(",")[1]

        attempt.upload_face_image(b64_face_image.decode('base64'))
        attempt.upload_photo_id_image(b64_photo_id_image.decode('base64'))
        attempt.mark_ready()

        attempt.save()

    course_id = request.POST['course_id']
    donation_for_course = request.session.get('donation_for_course', {})
    current_donation = donation_for_course.get(course_id, decimal.Decimal(0))
    contribution = request.POST.get("contribution", donation_for_course.get(course_id, 0))
    try:
        amount = decimal.Decimal(contribution).quantize(decimal.Decimal('.01'), rounding=decimal.ROUND_DOWN)
    except decimal.InvalidOperation:
        return HttpResponseBadRequest(_("Selected price is not valid number."))

    if amount != current_donation:
        donation_for_course[course_id] = amount
        request.session['donation_for_course'] = donation_for_course

    verified_mode = CourseMode.modes_for_course_dict(course_id).get('verified', None)

    # make sure this course has a verified mode
    if not verified_mode:
        return HttpResponseBadRequest(_("This course doesn't support verified certificates"))

    if amount < verified_mode.min_price:
        return HttpResponseBadRequest(_("No selected price or selected price is below minimum."))

    # I know, we should check this is valid. All kinds of stuff missing here
    cart = Order.get_cart_for_user(request.user)
    cart.clear()
    CertificateItem.add_to_order(cart, course_id, amount, 'verified')

    params = get_signed_purchase_params(cart)

    return HttpResponse(json.dumps(params), content_type="text/json")

@require_POST
@csrf_exempt # SS does its own message signing, and their API won't have a cookie value
def results_callback(request):
    """
    Software Secure will call this callback to tell us whether a user is
    verified to be who they said they are.
    """
    body = request.body
    body_dict = json.loads(body)
    headers = {
        "Authorization": request.META.get("HTTP_AUTHORIZATION", ""),
        "Date": request.META.get("HTTP_DATE", "")
    }

    sig_valid = ssencrypt.has_valid_signature(
        "POST",
        headers,
        body_dict,
        settings.VERIFY_STUDENT["SOFTWARE_SECURE"]["API_ACCESS_KEY"],
        settings.VERIFY_STUDENT["SOFTWARE_SECURE"]["API_SECRET_KEY"]
    )

    _, access_key_and_sig = headers["Authorization"].split(" ")
    access_key = access_key_and_sig.split(":")[0]

    # This is what we should be doing...
    #if not sig_valid:
    #    return HttpResponseBadRequest("Signature is invalid")

    # This is what we're doing until we can figure out why we disagree on sigs
    if access_key != settings.VERIFY_STUDENT["SOFTWARE_SECURE"]["API_ACCESS_KEY"]:
        return HttpResponseBadRequest("Access key invalid")

    receipt_id = body_dict.get("EdX-ID")
    result = body_dict.get("Result")
    reason = body_dict.get("Reason", "")
    error_code = body_dict.get("MessageType", "")

    try:
        attempt = SoftwareSecurePhotoVerification.objects.get(receipt_id=receipt_id)
    except SoftwareSecurePhotoVerification.DoesNotExist:
        log.error("Software Secure posted back for receipt_id {}, but not found".format(receipt_id))
        return HttpResponseBadRequest("edX ID {} not found".format(receipt_id))

    if result == "PASS":
        log.debug("Approving verification for {}".format(receipt_id))
        attempt.approve()
    elif result == "FAIL":
        log.debug("Denying verification for {}".format(receipt_id))
        attempt.deny(json.dumps(reason), error_code=error_code)
    elif result == "SYSTEM FAIL":
        log.debug("System failure for {} -- resetting to must_retry".format(receipt_id))
        attempt.system_error(json.dumps(reason), error_code=error_code)
        log.error("Software Secure callback attempt for %s failed: %s", receipt_id, reason)
    else:
        log.error("Software Secure returned unknown result {}".format(result))
        return HttpResponseBadRequest(
            "Result {} not understood. Known results: PASS, FAIL, SYSTEM FAIL".format(result)
        )

    return HttpResponse("OK!")

@login_required
def show_requirements(request, course_id):
    """
    Show the requirements necessary for
    """
    if CourseEnrollment.enrollment_mode_for_user(request.user, course_id) == 'verified':
        return redirect(reverse('dashboard'))

    course = course_from_id(course_id)
    context = {
        "course_id": course_id,
        "course_name": course.display_name_with_default,
        "course_org" : course.display_org_with_default,
        "course_num" : course.display_number_with_default,
        "is_not_active": not request.user.is_active,
    }
    return render_to_response("verify_student/show_requirements.html", context)


def show_verification_page(request):
    pass

def enroll(user, course_id, mode_slug):
    """
    Enroll the user in a course for a certain mode.

    This is the view you send folks to when they click on the enroll button.
    This does NOT cover changing enrollment modes -- it's intended for new
    enrollments only, and will just redirect to the dashboard if it detects
    that an enrollment already exists.
    """
    # If the user is already enrolled, jump to the dashboard. Yeah, we could
    # do upgrades here, but this method is complicated enough.
    if CourseEnrollment.is_enrolled(user, course_id):
        return HttpResponseRedirect(reverse('dashboard'))

    available_modes = CourseModes.modes_for_course(course_id)

    # If they haven't chosen a mode...
    if not mode_slug:
        # Does this course support multiple modes of Enrollment? If so, redirect
        # to a page that lets them choose which mode they want.
        if len(available_modes) > 1:
            return HttpResponseRedirect(
                reverse('choose_enroll_mode', kwargs={'course_id': course_id})
            )
        # Otherwise, we use the only mode that's supported...
        else:
            mode_slug = available_modes[0].slug

    # If the mode is one of the simple, non-payment ones, do the enrollment and
    # send them to their dashboard.
    if mode_slug in ("honor", "audit"):
        CourseEnrollment.enroll(user, course_id, mode=mode_slug)
        return HttpResponseRedirect(reverse('dashboard'))

    if mode_slug == "verify":
        if SoftwareSecurePhotoVerification.has_submitted_recent_request(user):
            # Capture payment info
            # Create an order
            # Create a VerifiedCertificate order item
            return HttpResponse.Redirect(reverse('verified'))

    # There's always at least one mode available (default is "honor"). If they
    # haven't specified a mode, we just assume it's
    if not mode:
        mode = available_modes[0]

    elif len(available_modes) == 1:
        if mode != available_modes[0]:
            raise Exception()

        mode = available_modes[0]

    if mode == "honor":
        CourseEnrollment.enroll(user, course_id)
        return HttpResponseRedirect(reverse('dashboard'))

