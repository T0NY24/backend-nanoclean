const express = require('express');

module.exports = function (prisma) {
  const router = express.Router();

  // GET /api/sensores -> últimas lecturas de ambos sensores
  router.get('/', async (req, res) => {
    try {
      // Obtenemos el último registro de sensor1
      const sensor1 = await prisma.sensorData.findFirst({
        where: { sensor: 'sensor1' },
        orderBy: { timestamp: 'desc' }
      });

      // Obtenemos el último registro de sensor2
      const sensor2 = await prisma.sensorData.findFirst({
        where: { sensor: 'sensor2' },
        orderBy: { timestamp: 'desc' }
      });

      res.json({
        sensor1: sensor1 || null,
        sensor2: sensor2 || null
      });
    } catch (error) {
      console.error('Error al obtener últimas lecturas:', error);
      res.status(500).json({ error: 'Error interno del servidor' });
    }
  });

  // GET /api/sensores/historial -> historial de lecturas (ej. últimos 50 registros)
  router.get('/historial', async (req, res) => {
    try {
      const limit = parseInt(req.query.limit) || 50;
      const historial = await prisma.sensorData.findMany({
        orderBy: { timestamp: 'desc' },
        take: limit
      });

      res.json(historial);
    } catch (error) {
      console.error('Error al obtener el historial:', error);
      res.status(500).json({ error: 'Error interno del servidor' });
    }
  });

  return router;
};
