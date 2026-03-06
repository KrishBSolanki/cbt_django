"""
Integration Module - Multi-DB Router
"""


class MultiDBRouter:
    """
    Database router for multi-database setup.
    Routes reads/writes to appropriate databases.
    """

    # Apps that use the default database
    DEFAULT_APPS = {'accounts', 'courses', 'questions', 'papers', 'auth', 'contenttypes', 'sessions', 'admin'}

    def db_for_read(self, model, **hints):
        """Direct reads to appropriate database"""
        app_label = model._meta.app_label
        if app_label in self.DEFAULT_APPS:
            return 'default'
        return 'default'

    def db_for_write(self, model, **hints):
        """Direct writes to default database only"""
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations if both models use the same database"""
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Only migrate Django apps on default database"""
        if db == 'default':
            return app_label in self.DEFAULT_APPS
        return False
