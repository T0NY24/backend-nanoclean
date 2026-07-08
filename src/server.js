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

const app = express();
const server = http.createServer(app);

// Configurar WebSockets
const io = new Server(server, {
  cors: {
    origin: '*',
    methods: ['GET', 'POST']
  }
});

// Middlewares
app.use(cors());
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

// WebSockets (Opcional, para loggear conexiones)
io.on('connection', (socket) => {
  console.log(`Cliente conectado: ${socket.id}`);
  socket.on('disconnect', () => {
    console.log(`Cliente desconectado: ${socket.id}`);
  });
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, '0.0.0.0', () => {
  console.log(`Servidor Express corriendo en el puerto ${PORT} y accesible desde la red local`);
});
