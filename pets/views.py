from rest_framework.views import APIView, status
from rest_framework.response import Response
from rest_framework.request import Request
from .models import Pet
from .serializers import PetSerializer
from groups.models import Group
from traits.models import Trait
from django.shortcuts import get_object_or_404
from rest_framework.pagination import PageNumberPagination


class PetView(APIView, PageNumberPagination):
    def get(self, request: Request) -> Response:
        scientific_name = request.query_params.get("scientific_name", None)
        trait = request.query_params.get("trait", None)
        if trait:
            trait = trait.lower()
        if scientific_name:
            scientific_name = scientific_name.lower()
        if scientific_name and trait:
            pets = Pet.objects.filter(
                traits__name=trait, group__scientific_name=scientific_name
            )
        elif trait and not scientific_name:
            pets = Pet.objects.filter(traits__name=trait)
        elif scientific_name and not trait:
            pets = Pet.objects.filter(group__scientific_name=scientific_name)
        else:
            pets = Pet.objects.all()

        result = self.paginate_queryset(pets, request, view=self)
        serializer = PetSerializer(result, many=True)

        return self.get_paginated_response(serializer.data)

    def post(self, request: Request):
        serializer = PetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group = serializer.validated_data.pop("group")
        list = []

        exist = Group.objects.filter(
            scientific_name__icontains=group["scientific_name"]
        )
        traits = serializer.validated_data.pop("traits")
        for trait in traits:
            trait_exist = Trait.objects.filter(name__icontains=trait["name"])

            trait_obj = (
                trait_exist.first()
                if trait_exist.exists()
                else Trait.objects.create(name=trait["name"].lower())
            )

            list.append(trait_obj)
        group_obj = (
            exist.first()
            if exist.exists()
            else Group.objects.create(scientific_name=group["scientific_name"].lower())
        )
        pet_obj = Pet.objects.create(**serializer.validated_data, group=group_obj)
        pet_obj.traits.set(list)
        serializer = PetSerializer(pet_obj)

        return Response(serializer.data, status.HTTP_201_CREATED)


class PetIdView(APIView):
    def get(self, request: Request, pet_id):
        pet = get_object_or_404(Pet, id=pet_id)
        serializer = PetSerializer(pet)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request: Request, pet_id):
        pet = get_object_or_404(Pet, id=pet_id)
        serializer = PetSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        list = []
        traits = serializer.validated_data.pop("traits", None)
        group = serializer.validated_data.pop("group", None)
        for key, value in serializer.validated_data.items():
            setattr(pet, key, value)

        if traits:
            for trait in traits:
                exist = Trait.objects.filter(name__icontains=trait["name"])
                trait_obj = (
                    exist.first()
                    if exist.exists()
                    else Trait.objects.create(name=trait["name"].lower())
                )
                list.append(trait_obj)

            pet.traits.set(list)

        if group:
            exist = Group.objects.filter(
                scientific_name__icontains=group["scientific_name"]
            )
            group_obj = (
                exist.first()
                if exist.exists()
                else Group.objects.create(
                    scientific_name=group["scientific_name"].lower()
                )
            )
            pet.group = group_obj
        pet.save()
        serializer = PetSerializer(pet)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request: Request, pet_id):
        pet = get_object_or_404(Pet, id=pet_id)
        pet.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
