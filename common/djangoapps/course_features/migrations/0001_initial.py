# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'CourseFeature'
        db.create_table('course_features_coursefeature', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('course_id', self.gf('django.db.models.fields.CharField')(max_length=255, db_index=True)),
            ('email_enabled', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('course_features', ['CourseFeature'])

        # Adding unique constraint on 'CourseFeature', fields ['course_id', 'email_enabled']
        db.create_unique('course_features_coursefeature', ['course_id', 'email_enabled'])


    def backwards(self, orm):
        # Removing unique constraint on 'CourseFeature', fields ['course_id', 'email_enabled']
        db.delete_unique('course_features_coursefeature', ['course_id', 'email_enabled'])

        # Deleting model 'CourseFeature'
        db.delete_table('course_features_coursefeature')


    models = {
        'course_features.coursefeature': {
            'Meta': {'unique_together': "(('course_id', 'email_enabled'),)", 'object_name': 'CourseFeature'},
            'course_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'email_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['course_features']