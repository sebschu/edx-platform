"""
Enable specific features for running courses on this particular LMS.

Migration Notes

If you make changes to this model, be sure to create an appropriate migration
file and check it in at the same time as your model changes. To do that,

1. Go to the edx-platform dir
2. ./manage.py lms schemamigration course_features --auto description_of_your_change
3. Add the migration file created in edx-platform/common/djangoapps/course_features/migrations/
"""
from django.db import models

from django.utils.translation import ugettext as _


class CourseFeature(models.Model):
    """
    Enable specific features on a course-by-course basis.
    """
    # The course that these features are attached to.
    course_id = models.CharField(max_length=255, db_index=True)

    # Whether or not to enable instructor email
    email_enabled = models.BooleanField(default=False)

    class Meta:
        """ meta attributes of this model """
        unique_together = ('course_id', 'email_enabled')

    @classmethod
    def instructor_email_enabled(cls, course_id):
        """
        Returns whether or not email is enabled for the given course id.

        If email has not been explicitly enabled, returns False.
        """
        try:
            record = cls.objects.get(course_id=course_id)
            return record.email_enabled
        except cls.DoesNotExist:
            return False

    def __unicode__(self):
        return u"Course {}: Instructor Email Enabled ({})".format(
            self.course_id, self.email_enabled
        )
