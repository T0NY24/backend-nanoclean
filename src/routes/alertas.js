const express = require('express');

module.exports = function (prisma) {
  const router = express.Router();

  // Obtener todas las alertas
  router.get('/', async (req, res) => {
    try {
      const alertas = await prisma.alerta.findMany({
        orderBy: { fecha: 'desc' }
      });
      res.json(alertas);
    } catch (error) {
      console.error('Error al obtener alertas:', error);
      res.status(500).json({ error: 'Error interno del servidor' });
    }
  });

  // Marcar una alerta como resuelta
  router.put('/:id/resolver', async (req, res) => {
    try {
      const { id } = req.params;
      const alerta = await prisma.alerta.update({
        where: { id: parseInt(id) },
        data: { estado: 'RESUELTA' }
      });
      res.json(alerta);
    } catch (error) {
      console.error('Error al resolver alerta:', error);
      res.status(500).json({ error: 'Error interno del servidor' });
    }
  });

  return router;
};
