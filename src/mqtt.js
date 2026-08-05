const mqtt = require('mqtt');

// Variables para evitar guardar en DB constantemente
const lastSaved = {
  sensor1: { distancia: null, time: 0 },
  sensor2: { distancia: null, time: 0 },
  sensor3: { distancia: null, time: 0 }
};

const CHANGE_THRESHOLD = 2.0; // cm de cambio para forzar guardado
const TIME_THRESHOLD = 5 * 60 * 1000; // 5 minutos en milisegundos

function setupMqtt(io, prisma) {
  const brokerUrl = process.env.MQTT_BROKER_URL;
  const options = {
    username: process.env.MQTT_USERNAME,
    password: process.env.MQTT_PASSWORD,
    protocol: 'mqtts',
    port: 8883,
    rejectUnauthorized: true,
    keepalive: 60, // Añadido para evitar timeouts frecuentes
  };

  const client = mqtt.connect(brokerUrl, options);

  client.on('connect', () => {
    console.log('Conectado a MQTT (HiveMQ Cloud)');
    client.subscribe(['nanoclean/sensor1', 'nanoclean/sensor2', 'nanoclean/sensor3'], (err) => {
      if (!err) {
        console.log('Suscrito a los topics: nanoclean/sensor1, nanoclean/sensor2, nanoclean/sensor3');
      } else {
        console.error('Error al suscribirse:', err);
      }
    });
  });

  client.on('message', async (topic, message) => {
    try {
      const distanciaStr = message.toString();
      const distancia = parseFloat(distanciaStr);
      const sensor = topic.split('/')[1];

      if (isNaN(distancia)) {
        return; // Ignorar invalidos
      }

      // Calculamos el porcentaje basado en la calibración real de cada contenedor (vacío = 0%)
      const ALTURAS_MAXIMAS = {
        sensor1: 33.80,
        sensor2: 34.97,
        sensor3: 31.56
      };
      
      const alturaMaxima = ALTURAS_MAXIMAS[sensor] || 30.0;
      let porcentajeLlenado = 100 - (distancia / alturaMaxima * 100);
      porcentajeLlenado = Math.max(0, Math.min(100, porcentajeLlenado));

      // 1. Emitir SIEMPRE por WebSockets (tiempo real para el dashboard)
      io.emit('sensorData', {
        sensor,
        distancia,
        porcentajeLlenado: parseFloat(porcentajeLlenado.toFixed(1)),
        timestamp: new Date()
      });

      // Lógica de creación de alerta al 85%
      if (porcentajeLlenado >= 85) {
        const alertaExistente = await prisma.alerta.findFirst({
          where: {
            contenedorId: sensor,
            tipo: 'LLENO',
            estado: 'PENDIENTE'
          }
        });

        if (!alertaExistente) {
          const nuevaAlerta = await prisma.alerta.create({
            data: {
              contenedorId: sensor,
              tipo: 'LLENO',
              ubicacion: `Contenedor ${sensor.replace('sensor', '')}`,
            }
          });
          io.emit('nuevaAlerta', nuevaAlerta);
          console.log(`[ALERTA] ${sensor} superó el 85%`);
        }
      }

      // 2. Lógica inteligente de guardado en DB
      const now = Date.now();
      const last = lastSaved[sensor];
      
      const hasSignificantChange = last.distancia === null || Math.abs(last.distancia - distancia) >= CHANGE_THRESHOLD;
      const isHeartbeatTime = (now - last.time) >= TIME_THRESHOLD;

      if (hasSignificantChange || isHeartbeatTime) {
        // Guardar en DB
        const savedData = await prisma.sensorData.create({
          data: {
            sensor,
            distancia
          }
        });
        
        console.log(`[DB SAVE] ${sensor} -> ${distancia}cm (Razón: ${hasSignificantChange ? 'Cambio significativo' : 'Latido'})`);
        
        // Actualizar caché
        lastSaved[sensor] = {
          distancia: savedData.distancia,
          time: now
        };
      }

    } catch (error) {
      console.error('Error al procesar mensaje MQTT:', error);
    }
  });

  client.on('error', (error) => {
    console.error('Error en conexión MQTT:', error);
  });
}

module.exports = setupMqtt;
