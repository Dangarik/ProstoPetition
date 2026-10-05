from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from petitions.models import Petition
from .services import cast_vote

class VoteView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        get_object_or_404(Petition, pk=pk)
        vote, count, petition_status, is_active = cast_vote(pk, request.user)
        return Response({"id": vote.id, "petition": pk, "vote_count": count,
                         "status": petition_status, "is_active": is_active}, status=201)

