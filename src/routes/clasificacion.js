const express = require('express');
const axios = require('axios');

const YOLO_SERVICE_URL = process.env.YOLO_SERVICE_URL || 'http://localhost:8000';

module.exports = function (prisma) {
  const router = express.Router();

  router.post('/', async (req, res) => {
    const { image, kioskId } = req.body;

    if (!image) {
      return res.status(400).json({ error: 'Falta el campo image (base64)' });
    }

    try {
      const response = await axios.post(
        `${YOLO_SERVICE_URL}/classify/base64`,
        { image },
        { timeout: 30000 }
      );

      const result = response.data;

      if (!result.success) {
        return res.status(400).json({
          error: result.error || 'Error en clasificación'
        });
      }

      const saved = await prisma.clasificacion.create({
        data: {
          contenedor: result.contenedor,
          claseDetectada: result.detection.class,
          confianza: result.detection.confidence,
          kioskId: kioskId || null
        }
      });

      res.json({
        id: saved.id,
        contenedor: result.contenedor,
        color: result.color,
        instruccion: result.instruccion,
        confianza: result.detection.confidence,
        clase: result.detection.class
      });

    } catch (error) {
      console.error('Error al clasificar:', error.message);

      if (error.code === 'ECONNREFUSED') {
        return res.status(503).json({
          error: 'Servicio de clasificación no disponible'
        });
      }

      res.status(500).json({ error: 'Error interno del servidor' });
    }
  });

  return router;
};
