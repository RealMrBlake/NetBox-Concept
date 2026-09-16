import django.core.validators
import django.db.models.deletion
import taggit.managers
import utilities.fields
import utilities.json
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('extras', '__latest__'),
        ('netbox_rack_concept', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConceptComponent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('custom_field_data', models.JSONField(
                    blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder
                )),
                ('component_type', models.CharField(max_length=50)),
                ('name', models.CharField(max_length=64)),
                ('label', models.CharField(blank=True, max_length=64)),
                ('port_type', models.CharField(blank=True, max_length=50)),
                ('positions', models.PositiveSmallIntegerField(default=1, validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(1024),
                ])),
                ('color', utilities.fields.ColorField(blank=True)),
                ('description', models.CharField(blank=True, max_length=200)),
                ('device', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='components',
                    to='netbox_rack_concept.conceptdevice'
                )),
                ('tags', taggit.managers.TaggableManager(through='extras.TaggedItem', to='extras.Tag')),
            ],
            options={
                'verbose_name': 'concept component',
                'verbose_name_plural': 'concept components',
                'ordering': ('device', 'component_type', 'name'),
            },
        ),
        migrations.AddConstraint(
            model_name='conceptcomponent',
            constraint=models.UniqueConstraint(fields=('device', 'name'), name='nbrc_component_unique_device_name'),
        ),
        migrations.CreateModel(
            name='ConceptPortMapping',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('front_position', models.PositiveSmallIntegerField(default=1)),
                ('rear_position', models.PositiveSmallIntegerField(default=1)),
                ('front_component', models.ForeignKey(
                    limit_choices_to={'component_type': 'front-port'},
                    on_delete=django.db.models.deletion.CASCADE, related_name='front_mappings',
                    to='netbox_rack_concept.conceptcomponent'
                )),
                ('rear_component', models.ForeignKey(
                    limit_choices_to={'component_type': 'rear-port'},
                    on_delete=django.db.models.deletion.CASCADE, related_name='rear_mappings',
                    to='netbox_rack_concept.conceptcomponent'
                )),
            ],
        ),
        migrations.AddConstraint(
            model_name='conceptportmapping',
            constraint=models.UniqueConstraint(
                fields=('front_component', 'front_position'), name='nbrc_portmapping_unique_front'
            ),
        ),
        migrations.AddConstraint(
            model_name='conceptportmapping',
            constraint=models.UniqueConstraint(
                fields=('rear_component', 'rear_position'), name='nbrc_portmapping_unique_rear'
            ),
        ),
        migrations.CreateModel(
            name='ConceptCable',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('custom_field_data', models.JSONField(
                    blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder
                )),
                ('status', models.CharField(default='connected', max_length=50)),
                ('type', models.CharField(blank=True, max_length=50)),
                ('color', utilities.fields.ColorField(blank=True)),
                ('label', models.CharField(blank=True, max_length=100)),
                ('description', models.CharField(blank=True, max_length=200)),
                ('comments', models.TextField(blank=True)),
                ('termination_a', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='+',
                    to='netbox_rack_concept.conceptcomponent'
                )),
                ('termination_b', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='+',
                    to='netbox_rack_concept.conceptcomponent'
                )),
                ('tags', taggit.managers.TaggableManager(through='extras.TaggedItem', to='extras.Tag')),
            ],
            options={
                'verbose_name': 'concept cable',
                'verbose_name_plural': 'concept cables',
                'ordering': ('pk',),
            },
        ),
    ]
