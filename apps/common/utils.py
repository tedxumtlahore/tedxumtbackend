from django.utils.text import slugify


def generate_unique_slug(instance, value, slug_field='slug'):
    model_class = instance.__class__
    base_slug = slugify(value)
    slug = base_slug
    counter = 1

    queryset = model_class._default_manager.all()
    if instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    while queryset.filter(**{slug_field: slug}).exists():
        slug = f'{base_slug}-{counter}'
        counter += 1

    return slug


def get_file_url(request, file_field):
    if not file_field:
        return None

    file_url = file_field.url
    if request is None:
        return file_url

    return request.build_absolute_uri(file_url)


def text_choices_to_dicts(choices_enum):
    return [{'value': choice.value, 'label': choice.label} for choice in choices_enum]
