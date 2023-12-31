import datetime
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Max
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from songs.models import Song, Playlist, Album
import shutil
import tempfile


MEDIA_ROOT = tempfile.mkdtemp()


class BaseAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)

        self.yesterday = datetime.date.today() - datetime.timedelta(days=1)
        self.tomorrow = datetime.date.today() + datetime.timedelta(days=1)

        self.old_user_data = {
            "username": "old_user",
            "password": "old_password",
            "first_name": "Old",
            "last_name": "User",
            "birth_date": self.yesterday,
            "country": "US",
            "email": "old_user@example.com"
        }
        self.old_user = get_user_model().objects.create_user(**self.old_user_data)

        self.old_user_2_data = {
            "username": "old_user_2",
            "password": "old_password_2"
        }
        self.old_user_2 = get_user_model().objects.create_user(**self.old_user_2_data)

        self.new_user_data = {
            "username": "new_user",
            "password": "new_password",
            "password_confirmation": "new_password",
            "first_name": "New",
            "last_name": "User",
            "birth_date": self.yesterday,
            "country": "BG",
            "email": "new_user@example.com"
        }


class RegistrationAPITest(BaseAPITest):
    def test_user_registration(self):
        """User registration should be successful with proper credentials and non-taken username."""
        response = self.client.post(reverse("songs:user-register"), self.new_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(get_user_model().objects.count(), 3)  # self.old_user, old_user_2 and new_user
        self.assertEqual(response.json()["user"]["username"], self.new_user_data["username"])
        self.assertIn("token", response.data)

    def test_user_registration_minimal_data(self):
        """User registration should be successful with proper credentials and non-taken username."""
        response = self.client.post(reverse(
            "songs:user-register"), {"username": "new_user", "password": "new_password", "password_confirmation": "new_password"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(get_user_model().objects.count(), 3)  # self.old_user, old_user_2 and new_user
        self.assertEqual(response.json()["user"]["username"], self.new_user_data["username"])
        self.assertIn("token", response.data)

    def test_fail_user_registration_username_taken(self):
        """User registration should fail if username is already taken."""
        self.old_user_data.update({"password_confirmation": self.old_user_data["password"]})
        response = self.client.post(reverse("songs:user-register"), self.old_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(get_user_model().objects.count(), 2)  # self.old_user and old_user_2
        self.assertEqual(response.json()["username"][0], "A user with that username already exists.")

    def test_fail_user_registration_password_mismatch(self):
        """User registration should fail if password_confirmation doesn't match password."""
        self.new_user_data["password_confirmation"] += "_2"
        response = self.client.post(reverse("songs:user-register"), self.new_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(get_user_model().objects.count(), 2)  # self.old_user and old_user_2
        self.assertEqual(response.json()["password_confirmation"][0], "Password confirmation does not match password.")

    def test_fail_user_registration_short_password(self):
        """User registration should fail if the provided password is less than 8 characters."""
        self.new_user_data["password"] = "pass"
        response = self.client.post(reverse("songs:user-register"), self.new_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(get_user_model().objects.count(), 2)  # self.old_user and old_user_2
        self.assertEqual(response.json()["password"][0], "This password is too short. It must contain at least 8 characters.")

    def test_fail_user_registration_future_birthday(self):
        """User registration should fail if the provided birth date is in the future."""
        self.new_user_data["birth_date"] = self.tomorrow
        response = self.client.post(reverse("songs:user-register"), self.new_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(get_user_model().objects.count(), 2)  # self.old_user and old_user_2
        self.assertRegex(response.json()["birth_date"][0], r"Ensure this value is less than or equal to \d{4}-\d{2}-\d{2}.")

    def test_fail_user_registration_invalid_country(self):
        """User registration should fail if the provided country doesn't exist."""
        self.new_user_data["country"] = "INVCNTR"
        response = self.client.post(reverse("songs:user-register"), self.new_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(get_user_model().objects.count(), 2)  # self.old_user and old_user_2
        self.assertRegex(response.json()["country"][0], r".* is not a valid choice.")

    def test_fail_user_registration_skip_username(self):
        """User registration should fail if username is not provided."""
        self.new_user_data.pop("username")
        response = self.client.post(reverse("songs:user-register"), self.new_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(get_user_model().objects.count(), 2)  # self.old_user and old_user_2
        self.assertEqual(response.json()["username"][0], "This field is required.")

    def test_fail_user_registration_skip_password(self):
        """User registration should fail if password is not provided."""
        self.new_user_data.pop("password")
        response = self.client.post(reverse("songs:user-register"), self.new_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(get_user_model().objects.count(), 2)  # self.old_user and old_user_2
        self.assertEqual(response.json()["password"][0], "This field is required.")

    def test_fail_user_registration_skip_password_confirmation(self):
        """User registration should fail if password confirmation is not provided."""
        self.new_user_data.pop("password_confirmation")
        response = self.client.post(reverse("songs:user-register"), self.new_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(get_user_model().objects.count(), 2)  # self.old_user and old_user_2
        self.assertEqual(response.json()["password_confirmation"][0], "This field is required.")

    def test_fail_registration_not_allowed_methods(self):
        """Check that get, put, patch and delete methods are not allowed for user login"""
        # get
        response = self.client.get(reverse("songs:user-register"))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # put
        response = self.client.put(reverse("songs:user-register"), self.new_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # patch
        response = self.client.patch(reverse("songs:user-register"), self.new_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # delete
        response = self.client.delete(reverse("songs:user-register"))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class LoginAPITest(BaseAPITest):
    def test_user_login(self):
        """User login should be successful correct credentials."""
        response = self.client.post(reverse("songs:user-login"), self.old_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["user"]["username"], self.old_user.username)
        self.assertIn("token", response.data)

    def test_fail_user_login_wrong_username(self):
        """User login should fail with incorrect credentials."""
        self.old_user_data["username"] += "_2"
        response = self.client.post(reverse("songs:user-login"), self.old_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["non_field_errors"][0], "Invalid Details.")

    def test_fail_user_login_wrong_password(self):
        """User login should fail with incorrect credentials."""
        self.old_user_data["password"] += "_2"
        response = self.client.post(reverse("songs:user-login"), self.old_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["non_field_errors"][0], "Invalid Details.")

    def test_fail_user_login_skip_username(self):
        """User login should fail if username is not provided."""
        self.old_user_data.pop("username")
        response = self.client.post(reverse("songs:user-login"), self.old_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["username"][0], "This field is required.")

    def test_fail_user_login_skip_password(self):
        """User login should fail if password is not provided."""
        self.old_user_data.pop("password")
        response = self.client.post(reverse("songs:user-login"), self.old_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["password"][0], "This field is required.")

    def test_fail_login_not_allowed_methods(self):
        """Check that get, put, patch and delete methods are not allowed for user login"""
        # get
        response = self.client.get(reverse("songs:user-login"))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # put
        response = self.client.put(reverse("songs:user-login"), self.old_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # patch
        response = self.client.patch(reverse("songs:user-login"), self.old_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # delete
        response = self.client.delete(reverse("songs:user-login"))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class BaseUnauthenticatedAPITest(BaseAPITest):
    def setUp(self):
        super().setUp()

        # simple dummy image for tests - png consisting of 1 white pixel
        image_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\r\xefF\xb8\x00\x00\x00\x00IEND\xaeB`\x82"

        self.old_album_data = {
            "title": "Old album",
            "release_date": self.yesterday,
            "artists": [self.old_user.id],
            "cover_image": SimpleUploadedFile(name="old_album_cover_image.png", content=image_content, content_type="image/png"),
        }

        # create an album and then set artists to prevent TypeError 
        album_artists = self.old_album_data.pop("artists")
        self.old_album = Album.objects.create(**self.old_album_data)
        self.old_album.artists.set(album_artists)

        self.old_song_data = {
            "title": "Old song",
            "audio_file": SimpleUploadedFile(name="old_audio_file.mp3", content=b"Old audio file content", content_type="audio/mp3"),
            "cover_image": SimpleUploadedFile(name="old_song_cover_image.png", content=image_content, content_type="image/png"),
            "release_date": self.yesterday,
            "artists": [self.old_user.id],
            "genre": "pop",
            "album": self.old_album,
            "track_number": 1
        }

        # create a song and then set artists to prevent TypeError 
        song_artists = self.old_song_data.pop("artists")
        self.old_song = Song.objects.create(**self.old_song_data)
        self.old_song.artists.set(song_artists)

        # create a song and then set artists to prevent TypeError 
        self.old_song_2 = Song.objects.create(**self.old_song_data)
        self.old_song_2.artists.set([self.old_user_2.id])

        self.new_song_data = {
            "title": "Old song",
            "audio_file": SimpleUploadedFile(name="new_audio_file.mp3", content=b"new audio file content", content_type="audio/mp3"),
            "cover_image": SimpleUploadedFile(name="new_song_cover_image.png", content=image_content, content_type="image/png"),
            "release_date": self.yesterday,
            "artists": [self.old_user.id],
            "genre": "rap",
            "album": self.old_album.id,
            "track_number": 3
        }

    @classmethod
    def tearDownClass(cls): 
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()


class BaseAuthenticatedAPITest(BaseUnauthenticatedAPITest):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.old_user)


class UnauthUserViewSetTest(BaseUnauthenticatedAPITest):
    def test_user_list(self):
        """Successfully list all users."""
        response = self.client.get(reverse("songs:users-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 2)  # list 2 users - old_user and old_user_2

    def test_get_user_detail(self):
        """Successfully get details of an existing user"""
        response = self.client.get(reverse("songs:users-detail", args=[self.old_user.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["username"], self.old_user.username)

    def test_fail_user_detail_read_password(self):
        """Make sure that user password not being sent"""
        response = self.client.get(reverse("songs:users-detail", args=[self.old_user.id]))
        with self.assertRaises(KeyError) as raises:
            response.json()["password"]

    def test_fail_user_detail_read_another_user_email(self):
        """Make sure that a user can't see another user"s email"""
        response = self.client.get(reverse("songs:users-detail", args=[self.old_user_2.id]))
        with self.assertRaises(KeyError) as raises:
            response.json()["email"]
        
    def test_fail_user_detail_invalid_id(self):
        """Fail to get details about a user with an invallid id"""
        response = self.client.get(
            reverse("songs:users-detail", args=[get_user_model().objects.all().aggregate(Max("id"))["id__max"] + 1]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        

class AuthUserViewSetTest(BaseAuthenticatedAPITest):
    def test_fail_user_list_not_allowed_methods(self):
        """Check that post, put, patch and delete methods are not allowed for user list"""
        # post
        response = self.client.post(reverse("songs:users-list"), self.new_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # put
        response = self.client.put(reverse("songs:users-list"))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # patch
        response = self.client.patch(reverse("songs:users-list"))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # delete
        response = self.client.delete(reverse("songs:users-list"))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_user_detail_put(self):
        """Test user can update all of their details"""
        self.new_user_data.update({"old_password": self.old_user_data["password"]})
        old_password_hash = self.old_user.password
        response = self.client.put(reverse("songs:users-detail", args=[self.old_user.id]), self.new_user_data, format="json")
        self.old_user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.old_user.username, self.new_user_data["username"])
        self.assertNotEqual(self.old_user.password, old_password_hash)

    def test_user_detail_change_username(self):
        """change username"""
        new_username = "available_username"
        response = self.client.patch(
            reverse("songs:users-detail", args=[self.old_user.id]), {"username": new_username}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["username"], new_username)

    def test_fail_user_detail_change_username_taken(self):
        """Assert user can't change their username to a taken one"""
        response = self.client.patch(
            reverse("songs:users-detail", args=[self.old_user.id]), {"username": self.old_user_2.username}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["username"][0], "A user with that username already exists.")

    def test_fail_user_detail_change_password_incorrect_old_password(self):
        """Assert user cant change their password if they input incorrect old password"""
        old_password = self.old_user.password
        response = self.client.patch(
            reverse("songs:users-detail", 
                    args=[self.old_user.id]),
            {"old_password": "incorrect password", 
             "password": self.new_user_data["password"], "password_confirmation": self.new_user_data["password"]}, 
            format="json")
        self.old_user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.old_user.password, old_password)
        self.assertEqual(response.json()["old_password"], "Old password is incorrect.")

    def test_fail_user_detail_change_password_too_short(self):
        """Assert user cant change their password if they input a short new password"""
        old_password = self.old_user.password
        response = self.client.patch(
            reverse("songs:users-detail", 
                    args=[self.old_user.id]),
            {"old_password": self.old_user_data["password"], "password": "short", "password_confirmation": "short"}, 
            format="json")
        self.old_user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.old_user.password, old_password)
        self.assertEqual(response.json()["password"][0], "This password is too short. It must contain at least 8 characters.")

    def test_fail_user_detail_change_password_skip_password_confirmation(self):
        """Assert user cant change their password if they don't provide their old password"""
        old_password = self.old_user.password
        response = self.client.patch(
            reverse("songs:users-detail", 
                    args=[self.old_user.id]),
            {"old_password": self.old_user_data["password"], "password": self.new_user_data["password"]}, 
            format="json")
        self.old_user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.old_user.password, old_password)
        self.assertEqual(response.json()["password_confirmation"][0], "Password confirmation does not match password.")

    def test_fail_user_detail_change_password_skip_old_password(self):
        """Assert user cant change their password if they don't privde password condirmation"""
        old_password = self.old_user.password
        response = self.client.patch(
            reverse("songs:users-detail", 
                    args=[self.old_user.id]),
            {"password": self.new_user_data["password"], "password_confirmation": self.new_user_data["password"]}, 
            format="json")
        self.old_user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.old_user.password, old_password)
        self.assertEqual(response.json()["old_password"], "Old password is incorrect.")

    def test_fail_user_post(self):
        """A user should be created only using register"""
        response = self.client.post(reverse("songs:users-list"))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_fail_user_detail_post(self):
        """A user should be created only using register"""
        response = self.client.post(reverse("songs:users-detail", args=[self.old_user.id]))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_user_detail_delete_user(self):
        """A user should be able to delete their profile."""
        response = self.client.delete(reverse("songs:users-detail", args=[self.old_user.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_fail_user_detail_modify_another_user(self):
        """
        Check that another user can't perform post, put, patch and delete methods
        Authenticated as old_user and attempt to send those requests to old_user_2
        """
        # post
        response = self.client.post(reverse("songs:users-detail", args=[self.old_user_2.id]))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # put
        response = self.client.put(reverse("songs:users-detail", args=[self.old_user_2.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # patch
        response = self.client.patch(reverse("songs:users-detail", args=[self.old_user_2.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # delete
        response = self.client.delete(reverse("songs:users-detail", args=[self.old_user_2.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UnauthSongTest(BaseUnauthenticatedAPITest):
    def test_song_list(self):
        """Successfully list all songs."""
        response = self.client.get(reverse("songs:songs-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 2)  # list 2 users - old_user and old_user_2

    def test_get_song_detail(self):
        """Successfully get details of an existing song"""
        response = self.client.get(reverse("songs:songs-detail", args=[self.old_song.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["title"], self.old_song.title)


class AuthSongTest(BaseAuthenticatedAPITest):
    def test_fail_song_list_not_allowed_methods(self):
        """Check that put, patch and delete methods are not allowed for song list"""
        # put
        response = self.client.put(reverse("songs:songs-list"))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # patch
        response = self.client.patch(reverse("songs:songs-list"))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # delete
        response = self.client.delete(reverse("songs:songs-list"))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_create_song(self):
        """Succesfully create a new song via post"""
        response = self.client.post(reverse("songs:songs-list"), data=self.new_song_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Song.objects.count(), 3)  # old_song, old_song_2 and new song
        self.assertEqual(response.json()["title"], self.new_song_data["title"])

    def test_fail_create_song_invalid_audio_file(self):
        """Fail to create a new song with an unsuported audio file format"""
        self.new_song_data["audio_file"] = self.new_song_data["cover_image"]
        response = self.client.post(reverse("songs:songs-list"), data=self.new_song_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Song.objects.count(), 2)  # old_song and old_song_2
        self.assertRegex(response.json()["audio_file"][0], 
                         r"File extension .* is not allowed. Allowed extensions are: mp3, wav, ogg.")

    def test_fail_create_song_invalid_cover_image(self):
        """Fail to create a new song with an unsuported image file format"""
        self.new_song_data["cover_image"] = SimpleUploadedFile(
            name="temp_audio_file.mp3", content=b"temp audio file content", content_type="audio/mp3")
        response = self.client.post(reverse("songs:songs-list"), data=self.new_song_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Song.objects.count(), 2)  # old_song and old_song_2
        self.assertEqual(response.json()["cover_image"][0], 
                         "Upload a valid image. The file you uploaded was either not an image or a corrupted image.")

    def test_fail_create_song_invalid_genre(self):
        """Fail to create a new song of an unsuported genre"""
        self.new_song_data["genre"] = "invgenre"
        response = self.client.post(reverse("songs:songs-list"), data=self.new_song_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Song.objects.count(), 2)  # old_song and old_song_2
        self.assertRegex(response.json()["genre"][0], r".*is not a valid choice.")

    def test_fail_create_song_future_release_date(self):
        """Fail to create a new song whose release date is in the future"""
        self.new_song_data["release_date"] = self.tomorrow
        response = self.client.post(reverse("songs:songs-list"), data=self.new_song_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Song.objects.count(), 2)  # old_song and old_song_2
        self.assertRegex(response.json()["release_date"][0], r"Ensure this value is less than or equal to \d{4}-\d{2}-\d{2}.")

    def test_fail_create_song_invalid_album(self):
        """Fail to create a new song associated with a non-existing album"""
        self.new_song_data["album"] = Album.objects.all().aggregate(Max("id"))["id__max"] + 1
        response = self.client.post(reverse("songs:songs-list"), data=self.new_song_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Song.objects.count(), 2)  # old_song and old_song_2
        self.assertRegex(response.json()["album"][0], r'Invalid pk ".*" - object does not exist.')

    def test_fail_create_song_invalid_track_number(self):
        """Fail to create a new song whose track number is less than 1."""
        self.new_song_data["track_number"] = -1
        response = self.client.post(reverse("songs:songs-list"), data=self.new_song_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Song.objects.count(), 2)  # old_song and old_song_2
        self.assertEqual(response.json()["track_number"][0], "Ensure this value is greater than or equal to 1.")

    def test_fail_create_song_missing_title(self):
        """Fail to create a new song with a blank title"""
        self.new_song_data.pop("title")
        response = self.client.post(reverse("songs:songs-list"), data=self.new_song_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Song.objects.count(), 2)  # old_song and old_song_2
        self.assertEqual(response.json()["title"][0], "This field is required.")

    def test_update_song(self):
        """Succesfully update song data"""
        response = self.client.put(
            reverse("songs:songs-detail", args=[self.old_song.id]), data=self.new_song_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["title"], self.new_song_data["title"])

    def test_update_song_title(self):
        """Succesfully update song title"""
        response = self.client.patch(
            reverse("songs:songs-detail", args=[self.old_song.id]), {"title": self.new_song_data["title"]}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["title"], self.new_song_data["title"])

    def test_update_song_audio_file(self):
        """Succesfully update song audio file"""
        response = self.client.patch(
            reverse("songs:songs-detail", args=[self.old_song.id]), {"title": self.new_song_data["title"]}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["title"], self.new_song_data["title"])

    def test_fail_update_album_by_other_artist(self):
        """Fail to associate a song with an album by another user"""
        album = Album.objects.create(title="Old album")
        album.artists.add(self.old_user_2)
        response = self.client.patch(
            reverse("songs:songs-detail", args=[self.old_song.id]), {"album": album.id}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(self.old_user in album.artists.all())
    
    def test_song_detail_delete_song(self):
        """A user should be able to delete a song of theirs."""
        response = self.client.delete(reverse("songs:songs-detail", args=[self.old_user.songs.first().id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_fail_modify_song_by_another_user(self):
        """Fail to modify a song by another artist"""
        response = self.client.post(reverse("songs:songs-detail", args=[self.old_song_2.id]), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.json()["detail"], 'Method "POST" not allowed.')

        response = self.client.put(reverse("songs:songs-detail", args=[self.old_song_2.id]), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()["detail"], "You do not have permission to perform this action.")

        response = self.client.patch(reverse("songs:songs-detail", args=[self.old_song_2.id]), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()["detail"], "You do not have permission to perform this action.")

        response = self.client.delete(reverse("songs:songs-detail", args=[self.old_song_2.id]), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()["detail"], "You do not have permission to perform this action.")

    def test_add_artist(self):
        """Add an artist to the list of artists associated with a song"""
        # request to add a user as an artist
        self.assertFalse(self.old_user_2 in self.old_song.artists.all())
        detail_url = reverse("songs:songs-detail", kwargs={"pk": self.old_song.id})
        custom_action_url = f"{detail_url}manage_requested_artists/"
        response = self.client.post(custom_action_url, {"artist_id": self.old_user_2.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.old_user_2 in self.old_song.requested_artists.all())
        self.assertEqual(self.old_song.requested_artists.count(), 1)

        # confirm to be added as an artist
        self.client.force_authenticate(user=self.old_user_2)
        custom_action_url = f"{detail_url}confirm_current_user_as_artist/"
        response = self.client.post(custom_action_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.old_user_2 in self.old_song.requested_artists.all())
        self.assertEqual(self.old_song.requested_artists.count(), 0)
        self.assertTrue(self.old_user_2 in self.old_song.artists.all())
        self.assertEqual(self.old_song.artists.count(), 2)  # old_user and old_user_2

    def test_fail_request_non_existing_artist(self):
        """Fail to request to add an artist with an invalid id to the list of artists associated with a song"""
        detail_url = reverse("songs:songs-detail", kwargs={"pk": self.old_song.id})
        custom_action_url = f"{detail_url}manage_requested_artists/"
        response = self.client.post(
            custom_action_url, {"artist_id": get_user_model().objects.all().aggregate(Max("id"))["id__max"] + 1})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["detail"], "Not found.")
        self.assertEqual(self.old_song.requested_artists.count(), 0)

    def test_remove_current_user_as_artist(self):
        """Remove the current user from the list of artists associated with a song"""
        self.assertTrue(self.old_user in self.old_song.artists.all())  # old_user
        detail_url = reverse("songs:songs-detail", kwargs={"pk": self.old_song.id})
        custom_action_url = f"{detail_url}remove_current_user_as_artist/"
        response = self.client.delete(custom_action_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.old_user in self.old_song.artists.all())
        self.assertEqual(self.old_song.artists.count(), 0)

    def test_remove_requested_artist(self):
        """Remove an artist from requested artists."""
        # request to add a user as an artist
        self.assertFalse(self.old_user_2 in self.old_song.artists.all())
        detail_url = reverse("songs:songs-detail", kwargs={"pk": self.old_song.id})
        custom_action_url = f"{detail_url}manage_requested_artists/"
        response = self.client.post(custom_action_url, {"artist_id": self.old_user_2.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.old_user_2 in self.old_song.requested_artists.all())
        self.assertEqual(self.old_song.requested_artists.count(), 1)

        # remove the requested artist from the requested artists list
        custom_action_url = f"{detail_url}manage_requested_artists/"
        response = self.client.delete(custom_action_url, {"artist_id": self.old_user_2.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.old_user_2 in self.old_song.requested_artists.all())
        self.assertEqual(self.old_song.requested_artists.count(), 0)
        self.assertFalse(self.old_user_2 in self.old_song.artists.all())
        self.assertEqual(self.old_song.artists.count(), 1)  # old_use


class BaseUnauthAlbumTest(BaseUnauthenticatedAPITest):
    def setUp(self):
        super().setUp()
        self.new_album_data = {
            "title": "New album",
            "release_date": self.yesterday,
            "artists": [self.old_user.id]
        }

        self.old_album_2_data = {
            "title": "Old album 2",
            "release_date": self.yesterday,
            "artists": [self.old_user_2.id]
        }

        # create an album and then set artists to prevent TypeError 
        album_artists = self.old_album_2_data.pop("artists")
        self.old_album_2 = Album.objects.create(**self.old_album_2_data)
        self.old_album_2.artists.set(album_artists)


class BaseAuthAlbumTest(BaseUnauthAlbumTest):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.old_user)


class AuthAlbumTest(BaseUnauthAlbumTest):
    def test_album_list(self):
        """Successfully list all albums."""
        response = self.client.get(reverse("songs:albums-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 2)  # old_album and old_album_2

    def test_get_album_detail(self):
        """Successfully get details of an existing album"""
        response = self.client.get(reverse("songs:albums-detail", args=[self.old_album.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["title"], self.old_album.title)


class AuthAlbumTest(BaseAuthAlbumTest):       

    def test_create_album(self):
        """Succesfully create a new album via post"""
        response = self.client.post(reverse("songs:albums-list"), data=self.new_album_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Album.objects.count(), 3)  # old_album, old_album_2 and new album
        self.assertEqual(response.json()["title"], self.new_album_data["title"])

    def test_fail_album_list_not_allowed_methods(self):
        """Check that put, patch and delete methods are not allowed for album list"""
        # put
        response = self.client.put(reverse("songs:albums-list"))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # patchAlbum.objects
        response = self.client.patch(reverse("songs:albums-list"))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # delete
        response = self.client.delete(reverse("songs:albums-list"))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_fail_create_album_invalid_cover_image(self):
        """Fail to create a new album with an unsuported image file format"""
        self.new_album_data["cover_image"] = SimpleUploadedFile(
            name="temp_audio_file.mp3", content=b"temp audio file content", content_type="audio/mp3")
        response = self.client.post(reverse("songs:albums-list"), data=self.new_album_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Album.objects.count(), 2)  # old_album and old_album_2
        self.assertEqual(response.json()["cover_image"][0], 
                         "Upload a valid image. The file you uploaded was either not an image or a corrupted image.")

    def test_fail_create_album_future_release_date(self):
        """Fail to create a new album whose release date is in the future"""
        self.new_album_data["release_date"] = self.tomorrow
        response = self.client.post(reverse("songs:albums-list"), data=self.new_album_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Album.objects.count(), 2)  # old_album and old_album_2
        self.assertRegex(response.json()["release_date"][0], r"Ensure this value is less than or equal to \d{4}-\d{2}-\d{2}.")

    def test_fail_create_album_missing_title(self):
        """Fail to create a new album with a blank title"""
        self.new_album_data.pop("title")
        response = self.client.post(reverse("songs:albums-list"), data=self.new_album_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Album.objects.count(), 2)  # old_album and old_album_2
        self.assertEqual(response.json()["title"][0], "This field is required.")

    def test_update_album(self):
        """Succesfully update album data"""
        response = self.client.put(
            reverse("songs:albums-detail", args=[self.old_album.id]), data=self.new_album_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["title"], self.new_album_data["title"])

    def test_update_album_title(self):
        """Succesfully update album title"""
        response = self.client.patch(
            reverse("songs:albums-detail", args=[self.old_album.id]), {"title": self.new_album_data["title"]}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["title"], self.new_album_data["title"])

    def test_album_detail_delete_album(self):
        """A user should be able to delete a album of theirs."""
        response = self.client.delete(reverse("songs:albums-detail", args=[self.old_user.albums.first().id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_fail_modify_album_by_another_user(self):
        """Fail to modify an album by another artist"""
        response = self.client.post(reverse("songs:albums-detail", args=[self.old_album_2.id]), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.json()["detail"], 'Method "POST" not allowed.')

        response = self.client.put(reverse("songs:albums-detail", args=[self.old_album_2.id]), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()["detail"], "You do not have permission to perform this action.")

        response = self.client.patch(reverse("songs:albums-detail", args=[self.old_album_2.id]), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()["detail"], "You do not have permission to perform this action.")

        response = self.client.delete(reverse("songs:albums-detail", args=[self.old_album_2.id]), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()["detail"], "You do not have permission to perform this action.")

    def test_add_artist(self):
        """Add an artist to the list of artists associated with an album"""
        self.assertFalse(self.old_user_2 in self.old_album.artists.all())
        detail_url = reverse("songs:albums-detail", kwargs={"pk": self.old_album.id})
        custom_action_url = f"{detail_url}manage_requested_artists/"
        response = self.client.post(custom_action_url, {"artist_id": self.old_user_2.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.old_user_2 in self.old_album.requested_artists.all())
        self.assertEqual(self.old_album.requested_artists.count(), 1)

        # confirm to be added as an artist
        self.client.force_authenticate(user=self.old_user_2)
        custom_action_url = f"{detail_url}confirm_current_user_as_artist/"
        response = self.client.post(custom_action_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.old_user_2 in self.old_album.requested_artists.all())
        self.assertEqual(self.old_album.requested_artists.count(), 0)
        self.assertTrue(self.old_user_2 in self.old_album.artists.all())
        self.assertEqual(self.old_album.artists.count(), 2)  # old_user and old_user_2

    def test_fail_request_non_existing_artist(self):
        """Fail to request to add an artist with an invalid id to the list of artists associated with an album"""
        detail_url = reverse("songs:albums-detail", kwargs={"pk": self.old_album.id})
        custom_action_url = f"{detail_url}manage_requested_artists/"
        response = self.client.post(
            custom_action_url, {"artist_id": get_user_model().objects.all().aggregate(Max("id"))["id__max"] + 1})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["detail"], "Not found.")
        self.assertEqual(self.old_album.requested_artists.count(), 0)  # old_user

    def test_remove_current_user_as_artist(self):
        """Remove the current user from the list of artists associated with an album"""
        self.assertTrue(self.old_user in self.old_album.artists.all())  # old_user
        detail_url = reverse("songs:albums-detail", kwargs={"pk": self.old_album.id})
        custom_action_url = f"{detail_url}remove_current_user_as_artist/"
        response = self.client.delete(custom_action_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.old_user in self.old_album.artists.all())
        self.assertEqual(self.old_album.artists.count(), 0)

    def test_remove_requested_artist(self):
        """Remove an artist from requested artists."""
        # request to add a user as an artist
        self.assertFalse(self.old_user_2 in self.old_album.artists.all())
        detail_url = reverse("songs:albums-detail", kwargs={"pk": self.old_album.id})
        custom_action_url = f"{detail_url}manage_requested_artists/"
        response = self.client.post(custom_action_url, {"artist_id": self.old_user_2.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.old_user_2 in self.old_album.requested_artists.all())
        self.assertEqual(self.old_album.requested_artists.count(), 1)

        # confirm to be added as an artist
        custom_action_url = f"{detail_url}manage_requested_artists/"
        response = self.client.delete(custom_action_url, {"artist_id": self.old_user_2.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.old_user_2 in self.old_album.requested_artists.all())
        self.assertEqual(self.old_album.requested_artists.count(), 0)
        self.assertFalse(self.old_user_2 in self.old_album.artists.all())
        self.assertEqual(self.old_album.artists.count(), 1)  # old_user


class BaseUnauthPlaylistTest(BaseUnauthenticatedAPITest):
    def setUp(self):
        super().setUp()
        self.old_playlist_title = "Old playlist"
        self.old_playlist = Playlist.objects.create(title=self.old_playlist_title, owner=self.old_user)
        self.old_playlist.songs.add(self.old_song)
        # self.old_playlist.songs.add(self.old_song_2)

        self.old_playlist_2_title = "Old playlist 2"
        self.old_playlist_2 = Playlist.objects.create(title=self.old_playlist_2_title, owner=self.old_user_2)
        self.old_playlist_2.songs.add(self.old_song)
        self.old_playlist_2.songs.add(self.old_song_2)

        self.new_playlist_title = "New Playlist"


class BasAauthPlaylistTest(BaseUnauthPlaylistTest):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.old_user)


class AuthPlaylistTest(BasAauthPlaylistTest):

    def test_playlist_list(self):
        """Successfully list all playlists by currrent user."""
        response = self.client.get(reverse("songs:playlists-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 1)  # old_playlist (old_playlist_2 is by another user)

    def test_fail_playlist_list_not_allowed_methods(self):
        """Check that put, patch and delete methods are not allowed for playlist list"""
        # put
        response = self.client.put(reverse("songs:playlists-list"))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # patchPlaylist.objects
        response = self.client.patch(reverse("songs:playlists-list"))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # delete
        response = self.client.delete(reverse("songs:playlists-list"))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_create_playlist(self):
        """Succesfully create a new playlist via post"""
        response = self.client.post(reverse("songs:playlists-list"), data={"title": self.new_playlist_title}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Playlist.objects.count(), 3)  # old_playlist, old_playlist_2 and new playlist
        self.assertEqual(response.json()["title"], self.new_playlist_title)
        # assert that old_user is set as playlist owner, because we are authenticated as old_user
        self.assertEqual(response.json()["owner"], self.old_user.id)

    def test_fail_create_playlist_missing_title(self):
        """Fail to create a new playlst with a blank title"""
        response = self.client.post(reverse("songs:playlists-list"), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Playlist.objects.count(), 2)  # old_playlist and old_playlist_2
        self.assertEqual(response.json()["title"][0], "This field is required.")

    def test_get_playlist_detail(self):
        """Successfully get details of an existing playlist"""
        response = self.client.get(reverse("songs:playlists-detail", args=[self.old_playlist.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["title"], self.old_playlist.title)
        # assert that old_user is set as playlist owner, because we are authenticated as old_user
        self.assertEqual(response.json()["owner"], self.old_user.id)
        self.assertEqual(response.json()["songs"], [song.id for song in self.old_playlist.songs.all()])

    def test_fail_get_playlist_by_another_user(self):
        """Fail to get details of another user"s playlist"""
        response = self.client.get(reverse("songs:playlists-detail", args=[self.old_playlist_2.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["detail"], "Not found.")

    def test_update_playlist_title(self):
        """Succesfully update playlist title"""
        response = self.client.patch(reverse("songs:playlists-detail", 
                                             args=[self.old_playlist.id]), {"title": self.new_playlist_title}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["title"], self.new_playlist_title)

    def test_fail_update_playlist_owner(self):
        """Fail to change the owner of a playlist (assign your playlist to another user)"""
        response = self.client.patch(reverse("songs:playlists-detail", 
                                             args=[self.old_playlist.id]), {"owner": self.old_user_2.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.json()["owner"], self.old_user_2.id)

    def test_playlist_detail_delete_playlist(self):
        """A user should be able to delete a playlist of theirs."""
        response = self.client.delete(reverse("songs:playlists-detail", args=[self.old_user.playlists.first().id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_fail_update_playlist_by_another_user(self):
        """Fail to modify a playlist by another user"""
        response = self.client.patch(reverse("songs:playlists-detail", args=[self.old_playlist_2.id]), format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["detail"], "Not found.")

        response = self.client.put(reverse("songs:playlists-detail", args=[self.old_playlist_2.id]), format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["detail"], "Not found.")

        response = self.client.patch(reverse("songs:playlists-detail", args=[self.old_playlist_2.id]), format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["detail"], "Not found.")

        response = self.client.delete(reverse("songs:playlists-detail", args=[self.old_playlist_2.id]), format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["detail"], "Not found.")

    def test_add_song(self):
        """Add a song to a playlist"""
        self.assertFalse(self.old_song_2 in self.old_playlist.songs.all())
        detail_url = reverse("songs:playlists-detail", kwargs={"pk": self.old_playlist.id})
        custom_action_url = f"{detail_url}manage_songs/"
        response = self.client.post(custom_action_url, {"song_id": self.old_song_2.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.old_song_2 in self.old_playlist.songs.all())
        self.assertEqual(self.old_playlist.songs.count(), 2)  # old_song and old_song_2

    def test_fail_add_non_existing_song(self):
        """Fail to add a song with an invalid id to a playlist"""
        detail_url = reverse("songs:playlists-detail", kwargs={"pk": self.old_playlist.id})
        custom_action_url = f"{detail_url}manage_songs/"
        response = self.client.post(custom_action_url, {"song_id": Song.objects.all().aggregate(Max("id"))["id__max"] + 1})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["detail"], "Not found.")
        self.assertEqual(self.old_playlist.songs.count(), 1)  # old_song

    def test_remove_song(self):
        """Remove a song from a playlist"""
        self.assertTrue(self.old_song in self.old_playlist.songs.all())  # old_song
        detail_url = reverse("songs:playlists-detail", kwargs={"pk": self.old_playlist.id})
        custom_action_url = f"{detail_url}manage_songs/"
        response = self.client.delete(custom_action_url, {"song_id": self.old_song.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.old_song in self.old_playlist.songs.all())
        self.assertEqual(self.old_playlist.songs.count(), 0)

    def test_fail_remove_non_existing_song(self):
        """Fail to remove a song with an invalid id from a playlist"""
        detail_url = reverse("songs:playlists-detail", kwargs={"pk": self.old_playlist.id})
        custom_action_url = f"{detail_url}manage_songs/"
        response = self.client.delete(custom_action_url, {"song_id": Song.objects.all().aggregate(Max("id"))["id__max"] + 1})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["detail"], "Not found.")
        self.assertEqual(self.old_playlist.songs.count(), 1)  # old_song