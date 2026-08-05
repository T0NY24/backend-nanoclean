-- CreateTable
CREATE TABLE "Alerta" (
    "id" SERIAL NOT NULL,
    "contenedorId" TEXT NOT NULL,
    "tipo" TEXT NOT NULL,
    "ubicacion" TEXT,
    "estado" TEXT NOT NULL DEFAULT 'PENDIENTE',
    "fecha" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Alerta_pkey" PRIMARY KEY ("id")
);
