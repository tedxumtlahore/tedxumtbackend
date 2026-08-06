"""Team serializers - departments and members."""

from rest_framework import serializers

from apps.common.utils import get_file_url

from .models import Department, TeamMember


class TeamMemberSerializer(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True)
    department_slug = serializers.CharField(source='department.slug', read_only=True)

    class Meta:
        model = TeamMember
        fields = [
            'id', 'name', 'slug', 'role', 'department', 'department_name', 'department_slug',
            'photo', 'bio', 'email', 'linkedin', 'instagram', 'order', 'is_visible',
            'created_at', 'updated_at', 'is_active',
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']

    def get_photo(self, obj):
        return get_file_url(self.context.get('request'), obj.photo)


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = [
            'id', 'name', 'slug', 'description', 'order', 'is_visible',
            'created_at', 'updated_at', 'is_active',
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']


class DepartmentDetailSerializer(DepartmentSerializer):
    """Department with its members nested — powers the grouped Team page."""

    members = serializers.SerializerMethodField()

    class Meta(DepartmentSerializer.Meta):
        fields = DepartmentSerializer.Meta.fields + ['members']

    def get_members(self, obj):
        members = [m for m in obj.members.all() if m.is_visible and m.is_active]
        return TeamMemberSerializer(members, many=True, context=self.context).data
