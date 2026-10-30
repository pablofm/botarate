from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """Hace explícita la tabla intermedia de Alumno.cursos, como el modelo Matrícula,
    para añadirle «exento_pago». La tabla y sus filas no cambian: en la base de datos
    solo se añade la columna."""

    dependencies = [
        ('clases', '0008_clase_reporte'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='Matrícula',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('alumno', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='matrículas', to='clases.alumno', verbose_name='alumna')),
                        ('curso', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='matrículas', to='clases.curso', verbose_name='curso')),
                    ],
                    options={
                        'verbose_name': 'Matrícula',
                        'verbose_name_plural': 'Matrículas',
                        'db_table': 'clases_alumno_cursos',
                        'unique_together': {('alumno', 'curso')},
                    },
                ),
                migrations.AlterField(
                    model_name='alumno',
                    name='cursos',
                    field=models.ManyToManyField(related_name='alumnos', through='clases.Matrícula', to='clases.curso', verbose_name='cursos'),
                ),
            ],
        ),
        migrations.AddField(
            model_name='matrícula',
            name='exento_pago',
            field=models.BooleanField(default=False, help_text='No paga este curso, así que no sale en el aviso de pagos pendientes.', verbose_name='exenta de pago'),
        ),
    ]
