from rest_framework import serializers

class BookSerializer(serializers.Serializer):
    work_id = serializers.CharField()
    title = serializers.CharField()
    authors = serializers.ListField(child=serializers.CharField(), default=list)
    first_publish_year = serializers.IntegerField(allow_null=True, required=False)
    cover_url = serializers.URLField(allow_null=True, required=False)

class ReadingListItemSerializer(serializers.Serializer):
    work_id = serializers.RegexField(r"^OL\d+W$")
    status = serializers.ChoiceField(["want_to_read", "reading", "finished"])
    rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    notes = serializers.CharField(max_length=500, required=False)

    def validate(self, data):
        if "rating" in data and data["status"] != "finished":
            raise serializers.ValidationError("rating is only allowed when status is 'finished'")
        return data