-- CreateTable
CREATE TABLE "SensorData" (
    "id" SERIAL NOT NULL,
    "sensor" TEXT NOT NULL,
    "distancia" DOUBLE PRECISION NOT NULL,
    "timestamp" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "SensorData_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Clasificacion" (
    "id" SERIAL NOT NULL,
    "contenedor" TEXT NOT NULL,
    "claseDetectada" TEXT NOT NULL,
    "confianza" DOUBLE PRECISION NOT NULL,
    "kioskId" TEXT,
    "timestamp" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Clasificacion_pkey" PRIMARY KEY ("id")
);
