"""
Test for Mock_Youtube_Server
"""
import unittest
import threading
import urllib
from mock_youtube_server import MockYoutubeServer

from nose.plugins.skip import SkipTest


class MockYoutubeServerTest(unittest.TestCase):
    '''
    A mock version of the Youtube provider server that listens on a local
    port and responds with jsonp.

    Used for lettuce BDD tests in lms/courseware/features/video.feature
    '''

    def setUp(self):

        # This is a test of the test setup,
        # so it does not need to run as part of the unit test suite
        # You can re-enable it by commenting out the line below
        # raise SkipTest

        # Create the server
        server_port = 8034
        server_host = '127.0.0.1'
        address = (server_host, server_port)
        self.server = MockYoutubeServer(address, )
        self.server.time_to_response = 0.5
        # Start the server in a separate daemon thread
        server_thread = threading.Thread(target=self.server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

    def tearDown(self):

        # Stop the server, freeing up the port
        self.server.shutdown()

    def test_request(self):
        """
        Tests that Youtube server processes request with right program
        path,  and responses with incorrect signature.
        """
        # GET request

        # unused url
        response_handle = urllib.urlopen(
            'http://127.0.0.1:8034/some url',
        )
        response = response_handle.read()
        self.assertEqual("""{"message": "Unused url"}""", response)

        # video player test url, callback shoud be presented in url params
        response_handle = urllib.urlopen(
            'http://127.0.0.1:8034/test_youtube/OEoXaMPEzfM?v=2&alt=jsonc&callback=callback_func',
        )
        response = response_handle.read()
        self.assertEqual("""callback_func({"message": "I\'m youtube."})""", response)

        # transcripts test url
        response_handle = urllib.urlopen(
            'http://127.0.0.1:8034/test_transcripts_youtube',
        )
        response = response_handle.read()
        self.assertEqual("""{"message": "Welcome transcripts."}""", response)
