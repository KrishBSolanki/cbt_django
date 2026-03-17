from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('courses', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=120, unique=True)),
                ('code', models.CharField(help_text='Short code e.g. COMM, MECH, ELEC, OPS', max_length=20, unique=True)),
                ('description', models.TextField(blank=True)),
                ('icon', models.CharField(default='🏢', help_text='Emoji shown in UI cards', max_length=10)),
                ('color_hex', models.CharField(default='#0ea5e9', help_text='Accent colour for UI e.g. #0ea5e9', max_length=7)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'db_table': 'dj_department', 'ordering': ['name'], 'verbose_name': 'Department'},
        ),
        migrations.CreateModel(
            name='ExamCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exam_categories', to='departments.department')),
            ],
            options={'db_table': 'dj_exam_category', 'ordering': ['department', 'order', 'name'], 'verbose_name': 'Exam Category', 'verbose_name_plural': 'Exam Categories'},
        ),
        migrations.CreateModel(
            name='Subject',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('code', models.CharField(blank=True, max_length=30)),
                ('description', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subjects', to='courses.course')),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subjects', to='departments.department')),
            ],
            options={'db_table': 'dj_subject', 'ordering': ['name'], 'verbose_name': 'Subject'},
        ),
        migrations.CreateModel(
            name='ExamBlueprint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('mcq_count', models.PositiveIntegerField(default=40)),
                ('mcq_marks', models.PositiveIntegerField(default=1)),
                ('descriptive_count', models.PositiveIntegerField(default=6)),
                ('descriptive_marks', models.PositiveIntegerField(default=10)),
                ('duration_minutes', models.PositiveIntegerField(default=180)),
                ('instructions', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blueprints', to='departments.examcategory')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blueprints', to='courses.course')),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blueprints', to='departments.department')),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blueprints', to='departments.subject')),
            ],
            options={'db_table': 'dj_exam_blueprint', 'ordering': ['department', 'category__order', 'course__course_code', 'subject__name'], 'verbose_name': 'Exam Blueprint'},
        ),
        migrations.CreateModel(
            name='BlueprintPaperGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('group_id', models.CharField(max_length=20, unique=True)),
                ('notes', models.TextField(blank=True)),
                ('generated_at', models.DateTimeField(auto_now_add=True)),
                ('blueprint', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='paper_groups', to='departments.examblueprint')),
                ('faculty', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bp_paper_groups', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'dj_blueprint_paper_group', 'ordering': ['-generated_at'], 'verbose_name': 'Blueprint Paper Group'},
        ),
        migrations.AddConstraint(
            model_name='examcategory',
            constraint=models.UniqueConstraint(fields=['department', 'name'], name='unique_dept_category'),
        ),
        migrations.AddConstraint(
            model_name='subject',
            constraint=models.UniqueConstraint(fields=['course', 'department', 'name'], name='unique_course_dept_subject'),
        ),
        migrations.AddConstraint(
            model_name='examblueprint',
            constraint=models.UniqueConstraint(fields=['department', 'category', 'course', 'subject'], name='unique_blueprint'),
        ),
    ]
