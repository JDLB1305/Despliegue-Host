$(document).ready(function() {
    var calendarEl = document.getElementById('calendar');

    var calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'timeGridWeek', // Vista semanal
        slotMinTime: '07:00:00', // Hora mínima (7 am)
        slotMaxTime: '22:00:00', // Hora máxima (10 pm)
        slotDuration: '01:00', // Intervalo de tiempo de 1 hora
        allDaySlot: false,
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'timeGridDay,timeGridWeek' // Opciones de vista
        },
        events: '/get_clases', // Cargar eventos desde el endpoint Flask
        eventClick: function(info) {
            // Lógica para inscribirse en la clase
            var classId = info.event.id; // Identificador de la clase
            var cupos = info.event.extendedProps.cupos_disponibles; // Cupos disponibles

            if (cupos > 0) {
                $.ajax({
                    url: '/inscribir_clase', // Endpoint para inscribirse
                    method: 'POST',
                    data: { clase_id: classId }, // Datos enviados al servidor
                    success: function(response) {
                        console.log('Inscrito en la clase:', response);
                        info.event.setProp('color', 'yellow'); // Cambiar color para indicar inscripción
                    },
                    error: function(error) {
                        console.error('Error al inscribirse:', error);
                    }
                });
            } else {
                alert('No hay cupos disponibles para esta clase.');
            }
        }
    });

    calendar.render(); // Renderizar el calendario
});