const express = require('express');

const ALTURA_MAXIMA = 30.0; // en cm
const CRITICAL_THRESHOLD = 80.0; // porcentaje
const ONLINE_THRESHOLD = 5 * 60 * 1000; // 5 minutos

module.exports = function (prisma) {
  const router = express.Router();

  router.get('/', async (req, res) => {
    try {
      const sensoresIds = ['sensor1', 'sensor2'];
      const contenedores = [];
      let contenedoresCriticos = 0;
      let sumaPorcentajes = 0;

      const historialData = {};

      for (const sensorId of sensoresIds) {
        // 1. Obtener registro más reciente
        const latest = await prisma.sensorData.findFirst({
          where: { sensor: sensorId },
          orderBy: { timestamp: 'desc' }
        });

        if (latest) {
          // Cálculo de porcentaje (invertido porque menor distancia = más lleno)
          let porcentajeLlenado = 100 - (latest.distancia / ALTURA_MAXIMA * 100);
          // Limitar entre 0 y 100
          porcentajeLlenado = Math.max(0, Math.min(100, porcentajeLlenado));
          
          const estadoCritico = porcentajeLlenado >= CRITICAL_THRESHOLD;
          if (estadoCritico) contenedoresCriticos++;
          
          sumaPorcentajes += porcentajeLlenado;

          // Verificar si está online
          const isOnline = (Date.now() - new Date(latest.timestamp).getTime()) <= ONLINE_THRESHOLD;

          // 2. Obtener última recolección (última vez que estuvo casi vacío, ej. distancia > 28cm)
          const lastCollection = await prisma.sensorData.findFirst({
            where: { 
              sensor: sensorId,
              distancia: { gte: 28.0 } 
            },
            orderBy: { timestamp: 'desc' }
          });

          contenedores.push({
            id: sensorId,
            distanciaActual: latest.distancia,
            porcentajeLlenado: parseFloat(porcentajeLlenado.toFixed(1)),
            estadoCritico,
            estadoSensor: isOnline ? 'ONLINE' : 'OFFLINE',
            ultimaRecoleccion: lastCollection ? lastCollection.timestamp : null,
            ultimoDato: latest.timestamp
          });
        }

        // 3. Obtener historial para gráficas (últimos 20 registros)
        const history = await prisma.sensorData.findMany({
          where: { sensor: sensorId },
          orderBy: { timestamp: 'desc' },
          take: 20
        });
        
        historialData[sensorId] = history.map(h => ({
          timestamp: h.timestamp,
          porcentaje: Math.max(0, Math.min(100, 100 - (h.distancia / ALTURA_MAXIMA * 100)))
        })).reverse(); // Invertir para que vaya de más antiguo a más nuevo
      }

      const totalContenedores = contenedores.length;
      const promedioLlenado = totalContenedores > 0 ? (sumaPorcentajes / totalContenedores).toFixed(1) : 0;

      res.json({
        resumen: {
          totalContenedores,
          contenedoresCriticos,
          promedioLlenado: parseFloat(promedioLlenado)
        },
        contenedores,
        historial: historialData
      });

    } catch (error) {
      console.error('Error al obtener datos del dashboard:', error);
      res.status(500).json({ error: 'Error interno del servidor' });
    }
  });

  return router;
};
