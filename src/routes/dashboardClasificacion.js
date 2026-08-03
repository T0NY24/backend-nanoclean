const express = require('express');

const CRITICAL_THRESHOLD = 80.0;

module.exports = function (prisma, io) {
  const router = express.Router();

  router.get('/resumen', async (req, res) => {
    try {
      const now = new Date();
      const startOfDay = new Date(now.setHours(0, 0, 0, 0));
      const startOfWeek = new Date(now.setDate(now.getDate() - 7));

      const [
        totalHoy,
        totalSemana,
        porContenedor,
        confianzaPromedio,
        ultimasClasificaciones
      ] = await Promise.all([
        prisma.clasificacion.count({
          where: { timestamp: { gte: startOfDay } }
        }),
        prisma.clasificacion.count({
          where: { timestamp: { gte: startOfWeek } }
        }),
        prisma.clasificacion.groupBy({
          by: ['contenedor'],
          _count: { contenedor: true },
          where: { timestamp: { gte: startOfWeek } }
        }),
        prisma.clasificacion.aggregate({
          _avg: { confianza: true },
          where: { timestamp: { gte: startOfWeek } }
        }),
        prisma.clasificacion.findMany({
          orderBy: { timestamp: 'desc' },
          take: 20
        })
      ]);

      const totalSemanaNum = totalSemana || 1;
      const distribucion = {};
      let totalCount = 0;

      porContenedor.forEach(item => {
        totalCount += item._count.contenedor;
      });

      porContenedor.forEach(item => {
        distribucion[item.contenedor] = {
          count: item._count.contenedor,
          porcentaje: parseFloat(((item._count.contenedor / totalCount) * 100).toFixed(1))
        };
      });

      const clasesCounts = {};
      ultimasClasificaciones.forEach(c => {
        clasesCounts[c.claseDetectada] = (clasesCounts[c.claseDetectada] || 0) + 1;
      });

      const objetosMasComunes = Object.entries(clasesCounts)
        .map(([clase, count]) => ({ clase, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 5);

      const clasificacionesPorHora = [];
      for (let i = 0; i < 24; i++) {
        const hourStart = new Date(startOfDay);
        hourStart.setHours(i);
        const hourEnd = new Date(startOfDay);
        hourEnd.setHours(i + 1);

        const count = await prisma.clasificacion.count({
          where: {
            timestamp: {
              gte: hourStart,
              lt: hourEnd
            }
          }
        });

        clasificacionesPorHora.push({ hora: i, count });
      }

      res.json({
        resumen: {
          totalClasificacionesHoy: totalHoy,
          totalClasificacionesSemana: totalSemana,
          confianzaPromedio: confianzaPromedio._avg.confianza
            ? parseFloat(confianzaPromedio._avg.confianza.toFixed(2))
            : 0,
          distribucionContenedores: distribucion,
          objetosMasComunes
        },
        clasificacionesPorHora,
        ultimasClasificaciones: ultimasClasificaciones.map(c => ({
          id: c.id,
          contenedor: c.contenedor,
          clase: c.claseDetectada,
          confianza: c.confianza,
          timestamp: c.timestamp
        }))
      });

    } catch (error) {
      console.error('Error al obtener resumen:', error);
      res.status(500).json({ error: 'Error interno del servidor' });
    }
  });

  router.get('/historial', async (req, res) => {
    try {
      const limit = parseInt(req.query.limit) || 50;
      const contenedor = req.query.contenedor;

      const where = {};
      if (contenedor) {
        where.contenedor = contenedor;
      }

      const historial = await prisma.clasificacion.findMany({
        where,
        orderBy: { timestamp: 'desc' },
        take: limit
      });

      res.json(historial);
    } catch (error) {
      console.error('Error al obtener historial:', error);
      res.status(500).json({ error: 'Error interno del servidor' });
    }
  });

  return router;
};
