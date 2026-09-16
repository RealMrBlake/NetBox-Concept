import django.core.validators
import django.db.models.deletion
import taggit.managers
import utilities.json
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        # __latest__ keeps the plugin ordered after every core migration, whichever
        # NetBox 4.6 patch release is installed.
        ('dcim', '__latest__'),
        ('extras', '__latest__'),
        ('tenancy', '__latest__'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RackConcept',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('custom_field_data', models.JSONField(
                    blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder
                )),
                ('name', models.CharField(max_length=100, unique=True)),
                ('status', models.CharField(default='draft', max_length=50)),
                ('form_factor', models.CharField(blank=True, max_length=50)),
                ('width', models.PositiveSmallIntegerField(default=19)),
                ('u_height', models.PositiveSmallIntegerField(default=42, validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(100),
                ])),
                ('starting_unit', models.PositiveSmallIntegerField(
                    default=1, validators=[django.core.validators.MinValueValidator(1)]
                )),
                ('desc_units', models.BooleanField(default=False)),
                ('outer_width', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('outer_height', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('outer_depth', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('outer_unit', models.CharField(blank=True, max_length=50)),
                ('mounting_depth', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('airflow', models.CharField(blank=True, max_length=50)),
                ('max_weight', models.PositiveIntegerField(blank=True, null=True)),
                ('description', models.CharField(blank=True, max_length=200)),
                ('comments', models.TextField(blank=True)),
                ('default_location', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+', to='dcim.location'
                )),
                ('default_site', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+', to='dcim.site'
                )),
                ('rack_role', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+', to='dcim.rackrole'
                )),
                ('rack_type', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name='rack_concepts', to='dcim.racktype'
                )),
                ('source_rack', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+', to='dcim.rack'
                )),
                ('tenant', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name='rack_concepts', to='tenancy.tenant'
                )),
                ('tenant_group', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name='rack_concepts', to='tenancy.tenantgroup'
                )),
                ('tags', taggit.managers.TaggableManager(through='extras.TaggedItem', to='extras.Tag')),
            ],
            options={
                'verbose_name': 'rack concept',
                'verbose_name_plural': 'rack concepts',
                'ordering': ('name',),
            },
        ),
        migrations.CreateModel(
            name='ConceptDevice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('custom_field_data', models.JSONField(
                    blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder
                )),
                ('name', models.CharField(blank=True, max_length=64)),
                ('status', models.CharField(default='planned', max_length=50)),
                ('position', models.DecimalField(
                    blank=True, decimal_places=1, max_digits=4, null=True,
                    validators=[django.core.validators.MinValueValidator(0.5)]
                )),
                ('face', models.CharField(default='front', max_length=50)),
                ('width_fraction', models.PositiveSmallIntegerField(default=1)),
                ('horizontal_position', models.PositiveSmallIntegerField(default=0)),
                ('u_height', models.DecimalField(
                    blank=True, decimal_places=1, max_digits=4, null=True,
                    validators=[django.core.validators.MinValueValidator(0)]
                )),
                ('is_full_depth', models.BooleanField(blank=True, null=True)),
                ('serial', models.CharField(blank=True, max_length=50)),
                ('label', models.CharField(blank=True, max_length=64)),
                ('description', models.CharField(blank=True, max_length=200)),
                ('comments', models.TextField(blank=True)),
                ('concept', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='devices',
                    to='netbox_rack_concept.rackconcept'
                )),
                ('device_type', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name='concept_devices', to='dcim.devicetype'
                )),
                ('platform', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name='concept_devices', to='dcim.platform'
                )),
                ('role', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name='concept_devices', to='dcim.devicerole'
                )),
                ('source_device', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+', to='dcim.device'
                )),
                ('tenant', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name='concept_devices', to='tenancy.tenant'
                )),
                ('tags', taggit.managers.TaggableManager(through='extras.TaggedItem', to='extras.Tag')),
            ],
            options={
                'verbose_name': 'concept device',
                'verbose_name_plural': 'concept devices',
                'ordering': ('concept', '-position', 'horizontal_position', 'pk'),
            },
        ),
        migrations.CreateModel(
            name='ConceptDeployment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('rack_name', models.CharField(max_length=100)),
                ('device_count', models.PositiveSmallIntegerField(default=0)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('concept', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='deployments',
                    to='netbox_rack_concept.rackconcept'
                )),
                ('rack', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+', to='dcim.rack'
                )),
                ('user', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+', to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'verbose_name': 'concept deployment',
                'verbose_name_plural': 'concept deployments',
                'ordering': ('-created',),
            },
        ),
        migrations.AddIndex(
            model_name='conceptdevice',
            index=models.Index(fields=['concept', 'position'], name='nbrc_device_concept_pos_idx'),
        ),
    ]
