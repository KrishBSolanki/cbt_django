"""
Management command: sync_moodle_questions
Usage: python manage.py sync_moodle_questions
"""
from django.core.management.base import BaseCommand
from integration.sync import (
    sync_courses_from_moodle,
    sync_quizzes_from_moodle,
    sync_questions_from_moodle,
)


class Command(BaseCommand):
    help = 'Sync questions from Moodle and courses from TRMS databases'

    def add_arguments(self, parser):
        parser.add_argument(
            '--module',
            type=str,
            choices=['all', 'moodle_courses', 'moodle_quizzes', 'moodle_questions'],
            default='all',
            help='Which module to sync (default: all)',
        )

    def handle(self, *args, **options):
        module = options['module']

        self.stdout.write(self.style.WARNING(f'\n🔄 Starting sync: {module}\n'))

        if module in ('all', 'moodle_courses'):
            self.stdout.write('📗 Syncing courses from Moodle...')
            try:
                stats = sync_courses_from_moodle()
                self.stdout.write(self.style.SUCCESS(
                    f'   ✅ Moodle Courses: {stats["created"]} created, {stats["updated"]} updated'
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ❌ Moodle courses sync failed: {e}'))

        if module in ('all', 'moodle_quizzes'):
            self.stdout.write('📙 Syncing quizzes from Moodle...')
            try:
                stats = sync_quizzes_from_moodle()
                self.stdout.write(self.style.SUCCESS(
                    f'   ✅ Moodle Quizzes: {stats["created"]} created, {stats["updated"]} updated'
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ❌ Moodle quizzes sync failed: {e}'))

        if module in ('all', 'moodle_questions'):
            self.stdout.write('📕 Syncing questions from Moodle...')
            try:
                stats = sync_questions_from_moodle()
                self.stdout.write(self.style.SUCCESS(
                    f'   ✅ Moodle Questions: {stats["questions_created"]} created, {stats["questions_updated"]} updated, {stats["answers_created"]} answers'
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ❌ Moodle questions sync failed: {e}'))

        self.stdout.write(self.style.SUCCESS('\n✅ Sync complete!\n'))
