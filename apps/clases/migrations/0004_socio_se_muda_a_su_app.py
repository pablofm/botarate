"""La otra mitad del traslado de Socio a la app «socios».

En el estado se apunta Alumno.socio al modelo nuevo y se borra el viejo; en la
base de datos basta con renombrar la tabla, que conserva filas, secuencia,
índices y claves ajenas.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clases', '0003_consentimientos_del_socio'),
        ('socios', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='alumno',
                    name='socio',
                    field=models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='alumno', to='socios.socio', verbose_name='socio'),
                ),
                migrations.DeleteModel(name='Socio'),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql='ALTER TABLE clases_socio RENAME TO socios_socio;',
                    reverse_sql='ALTER TABLE socios_socio RENAME TO clases_socio;'),
            ],
        ),
    ]
