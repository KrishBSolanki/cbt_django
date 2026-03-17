# """
# Integration Module - Multi-DB Router
# """


# class MultiDBRouter:
#     """
#     Database router for multi-database setup.
#     Routes reads/writes to appropriate databases.
#     """

#     # Apps that use the default database
#     DEFAULT_APPS = {'accounts', 'courses', 'questions', 'papers', 'auth', 'contenttypes', 'sessions', 'admin'}

#     def db_for_read(self, model, **hints):
#         """Direct reads to appropriate database"""
#         app_label = model._meta.app_label
#         if app_label in self.DEFAULT_APPS:
#             return 'default'
#         return 'default'

#     def db_for_write(self, model, **hints):
#         """Direct writes to default database only"""
#         return 'default'

#     def allow_relation(self, obj1, obj2, **hints):
#         """Allow relations if both models use the same database"""
#         return True

#     def allow_migrate(self, db, app_label, model_name=None, **hints):
#         """Only migrate Django apps on default database"""
#         if db == 'default':
#             return app_label in self.DEFAULT_APPS
#         return False
"""
Integration Module - Multi-DB Router
Routes Django apps to correct databases.
"""


class MultiDBRouter:
    """
    Router for handling multiple databases.

    default  -> main CBT system
    moodle   -> Moodle question bank
    trms     -> TRMS external system
    """

    # Apps that belong to the main CBT system
    DEFAULT_APPS = {
        'accounts',
        'courses',
        'questions',
        'papers',
        'departments',   # ⭐ IMPORTANT (new app)
        'auth',
        'contenttypes',
        'sessions',
        'admin'
    }
    TRMS_APPS = {
    'trms_models'
}

    # Apps that belong to Moodle integration
    MOODLE_APPS = {
        'integration'
    }

    def db_for_read(self, model, **hints):
        """Route read queries"""
        app_label = model._meta.app_label

        if app_label in self.MOODLE_APPS:
            return 'moodle'
        if app_label in self.TRMS_APPS:
            return 'trms'
        
        return 'default'

    def db_for_write(self, model, **hints):
        """Route write queries"""
        app_label = model._meta.app_label

        if app_label in self.MOODLE_APPS:
            return 'moodle'
        if app_label in self.TRMS_APPS:
            return False
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations between objects"""
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Control which database migrations run on
        """

        # Moodle models → moodle database
        if app_label in self.MOODLE_APPS:
            return db == 'moodle'

        # All CBT system apps → default database
        if app_label in self.DEFAULT_APPS:
            return db == 'default'

        # Block everything else
        return False