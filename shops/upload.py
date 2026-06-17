import cloudinary.uploader
from rest_framework import permissions, response, status, views
from rest_framework.parsers import MultiPartParser


class CloudinaryUploadView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = (MultiPartParser,)

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return response.Response(
                {"detail": "No file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = cloudinary.uploader.upload(file)
        return response.Response({"url": result["secure_url"]})
