const fs = require('fs');
const { parse } = require('csv-parse/sync');
const { Client } = require('pg');

const DB_CONFIG = {
  host: '192.168.1.175',
  port: 5432,
  database: 'capalsa',
  user: 'capalsa',
  password: 'capalsa2026',
};

const CSV_PATH = './csv/pedidos_consolidados.csv';

async function upsert() {
  const content = fs.readFileSync(CSV_PATH, 'utf8');
  const rows = parse(content, { columns: true, skip_empty_lines: true, relax_quotes: true });

  const client = new Client(DB_CONFIG);
  await client.connect();

  let insertados = 0;
  let duplicados = 0;

  for (const row of rows) {
    const res = await client.query(`
      INSERT INTO ventas (
        id_pedido, fecha_pedido, producto, asin, sku, cantidad,
        subtotal, fecha_limite_envio, estado_pedido, fecha_procesado,
        direccion_envio, telefono_comprador, subtotal_productos,
        costo_envio, total_antes_impuestos, impuestos, total_pedido
      ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)
      ON CONFLICT (id_pedido) DO NOTHING
    `, [
      row.id_pedido,
      row.fecha_pedido || null,
      row.producto,
      row.asin,
      row.sku,
      parseInt(row.cantidad) || 1,
      parseFloat(row.subtotal) || null,
      row.fecha_limite_envio || null,
      row.estado_pedido,
      row.fecha_procesado || null,
      row.direccion_envio,
      row.telefono_comprador,
      parseFloat(row.subtotal_productos) || null,
      parseFloat(row.costo_envio) || null,
      parseFloat(row.total_antes_impuestos) || null,
      parseFloat(row.impuestos) || null,
      parseFloat(row.total_pedido) || null,
    ]);

    if (res.rowCount > 0) insertados++;
    else duplicados++;
  }

  await client.end();
  console.log(`✅ Listo. Insertados: ${insertados} | Ya existían: ${duplicados} | Total CSV: ${rows.length}`);
}

upsert().catch(err => {
  console.error('❌ Error:', err.message);
  process.exit(1);
});
