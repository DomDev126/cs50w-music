from django.contrib.auth.hashers import check_password
from django.shortcuts import get_object_or_404
from .helpers import add_artist_to_requested, remove_artist_from_requested, confirm_user_as_artist, remove_user_as_artist, add_song_to_playlist, remove_song_from_playlist
from knox.models import AuthToken
from .models import User, Song, Playlist, Album
from .permissions import IsArtistOrReadOnly, IsPlaylistOwner, IsUserOrReadOnly, IsRequestedArtist
from rest_framework import viewsets, generics, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import UserSerializer, LoginUserSerializer, SongSerializer, PlaylistSerializer, AlbumSerializer


class UserViewSet(viewsets.ModelViewSet):
    """API endpoint that allows Users to be viewed or edited."""

    queryset = User.objects.all().order_by("username")
    permission_classes = [IsUserOrReadOnly]
    serializer_class = UserSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["username", "country"]

    def create(self, request, *args, **kwargs):
        """A new user should be created using register."""
        return Response({"detail": "Use register."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete the user"""
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RegistrationAPI(generics.GenericAPIView):
    """API endpoint that allows new Users to be created."""

    authentication_classes = []
    serializer_class = UserSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
            "token": AuthToken.objects.create(user)[1]
        }, status=status.HTTP_201_CREATED)


class LoginAPI(generics.GenericAPIView):
    """API endpoint that allows users to be authenticated."""

    authentication_classes = []
    serializer_class = LoginUserSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
            "token": AuthToken.objects.create(user)[1]
        })


class ReleaseMixin:
    """Functionalities that are common between songs and albums"""
    
    def perform_create(self, serializer):
        """Automatically add the current user to the list of artists"""
        entity_instance = serializer.save()
        entity_instance.artists.add(self.request.user)

    @action(detail=True, methods=["post", "delete"])
    def manage_requested_artists(self, request, pk=None):
        """Add/remove an artist to/from requested artists."""
        entity = self.get_object()
        artist_id = request.data.get("artist_id")
        if artist_id is None:
            return Response({"artist_id": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
    
        artist = get_object_or_404(User, pk=artist_id)

        if request.method == "POST":
            return add_artist_to_requested(entity, artist, request.user)
        else:
            return remove_artist_from_requested(entity, artist, request.user)

    @action(detail=True, methods=["post"], permission_classes=[IsRequestedArtist])
    def confirm_current_user_as_artist(self, request, pk=None):
        """Add the current user to the artists list if they are in requested artists."""
        return confirm_user_as_artist(self.get_object(), request.user)
    
    @action(detail=True, methods=["delete"])
    def remove_current_user_as_artist(self, request, pk=None):
        """Remove current user from the artists list"""
        return remove_user_as_artist(self.get_object(), request.user)
    

class SongViewSet(ReleaseMixin, viewsets.ModelViewSet):
    """API endpoint that allows Songs to be viewed or edited."""

    queryset = Song.objects.all().order_by("-release_date")
    serializer_class = SongSerializer
    permission_classes = [IsArtistOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ["title", "artists__username"]


class AlbumViewSet(ReleaseMixin, viewsets.ModelViewSet):
    """API endpoint that allows Albums to be viewed or edited."""

    queryset = Album.objects.all().order_by("-release_date")
    serializer_class = AlbumSerializer
    permission_classes = [IsArtistOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ["title", "artists__username"]


class PlaylistViewSet(viewsets.ModelViewSet):
    """API endpoint that allows Playlists to be viewed or edited."""

    serializer_class = PlaylistSerializer
    permission_classes = [IsPlaylistOwner]
    filter_backends = [filters.SearchFilter]
    search_fields = ["title"]

    def get_queryset(self):
        return Playlist.objects.filter(owner=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        """Set the user as the owner of the playlist"""
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["post", "delete"])
    def manage_songs(self, request, pk=None):
        """Add/remove a song to/from a playlist."""

        playlist = self.get_object()
        song_id = request.data.get("song_id")
        if song_id is None:
            return Response({"song_id": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        song = get_object_or_404(Song, pk=song_id)

        if request.method == "POST":
            return add_song_to_playlist(playlist, song)
        else:
            return remove_song_from_playlist(playlist, song)