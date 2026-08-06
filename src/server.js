require('dotenv').config();
const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');
const { PrismaClient } = require('@prisma/client');
const { Pool } = require('pg');
const { PrismaPg } = require('@prisma/adapter-pg');
const setupMqtt = require('./mqtt');
const sensoresRouter = require('./routes/sensores');
const dashboardRouter = require('./routes/dashboard');
const clasificacionRouter = require('./routes/clasificacion');
const dashboardClasificacionRouter = require('./routes/dashboardClasificacion');
const alertasRouter = require('./routes/alertas');

const app = express();
const server = http.createServer(app);

const allowedOrigins = [
  'https://nanoclean.uidehub.tech',
  'https://api-nano-clean.uidehub.tech',
  'https://api-yolo.uidehub.tech',
  'http://localhost:3000',
  'http://localhost:3001',
  'http://localhost:3006',
  'http://127.0.0.1:3000',
  'http://127.0.0.1:3001',
  'http://127.0.0.1:3006'
];

// Configurar WebSockets
const io = new Server(server, {
  cors: {
    origin: allowedOrigins,
    methods: ['GET', 'POST'],
    credentials: true
  }
});

// Middlewares
app.use(cors({
  origin: function (origin, callback) {
    // Permitir peticiones sin origen (como scripts locales, MQTT, Postman o curl)
    if (!origin) return callback(null, true);
    if (allowedOrigins.indexOf(origin) !== -1 || origin.startsWith('http://localhost') || origin.startsWith('http://127.0.0.1')) {
      return callback(null, true);
    }
    return callback(new Error('Bloqueado por política CORS'));
  },
  credentials: true
}));
app.use(express.json());

// Prisma Client
const pool = new Pool({ connectionString: process.env.DATABASE_URL });
const adapter = new PrismaPg(pool);
const prisma = new PrismaClient({ adapter });

// Hacer io y prisma accesibles en las rutas si fuera necesario, o pasarlo a módulos
// Para simplificar, pasamos io y prisma a las funciones que lo requieran.

// Iniciar MQTT
setupMqtt(io, prisma);

// Rutas
app.use('/api/sensores', sensoresRouter(prisma));
app.use('/api/dashboard', dashboardRouter(prisma));
app.use('/api/clasificar', clasificacionRouter(prisma));
app.use('/api/dashboard/clasificacion', dashboardClasificacionRouter(prisma, io));
app.use('/api/alertas', alertasRouter(prisma));

// Endpoint interno para recibir clasificaciones del microservicio YOLO (tiempo real)
app.post('/api/clasificar/internal', async (req, res) => {
  try {
    const { contenedor, claseDetectada, confianza, color, instruccion, bbox } = req.body;

    const saved = await prisma.clasificacion.create({
      data: {
        contenedor,
        claseDetectada,
        confianza
      }
    });

    const responseData = {
      id: saved.id,
      contenedor,
      color,
      instruccion,
      confianza,
      clase: claseDetectada,
      timestamp: saved.timestamp,
      bbox
    };

    // Emitir por WebSocket para dashboard en tiempo real
    io.emit('clasificacionDetectada', responseData);

    res.json(responseData);
  } catch (error) {
    console.error('Error guardando clasificación interna:', error);
    res.status(500).json({ error: 'Error interno del servidor' });
  }
});

// WebSockets (Opcional, para loggear conexiones)
io.on('connection', (socket) => {
  console.log(`Cliente conectado: ${socket.id}`);
  socket.on('disconnect', () => {
    console.log(`Cliente desconectado: ${socket.id}`);
  });
});

const PORT = process.env.PORT || 3001;
const HOST = process.env.HOST || '0.0.0.0';
server.listen(PORT, HOST, () => {
  console.log(`Servidor Express corriendo en http://${HOST}:${PORT}`);
});
