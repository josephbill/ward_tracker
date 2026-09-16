/**
 * HTTP sidecar Flask's app/services/ledger/hedera_sidecar_client.py talks
 * to. See hedera.js for the actual Hedera Consensus Service calls.
 */
require("dotenv/config");
const express = require("express");
const { submitEvent, verifyEvent } = require("./hedera");

const app = express();
app.use(express.json());

app.post("/submit", async (req, res) => {
  try {
    const { event_type, payload_hash } = req.body;
    if (!event_type || !payload_hash) {
      return res.status(400).json({ error: "event_type and payload_hash are required" });
    }
    const result = await submitEvent(event_type, payload_hash);
    res.json(result);
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

app.get("/verify", async (req, res) => {
  try {
    const { ledger_ref, payload_hash } = req.query;
    if (!ledger_ref || !payload_hash) {
      return res.status(400).json({ error: "ledger_ref and payload_hash are required" });
    }
    const valid = await verifyEvent(payload_hash, ledger_ref);
    res.json({ valid });
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

app.get("/healthz", (_req, res) => res.json({ status: "ok" }));

const port = process.env.PORT || 4001;
app.listen(port, () => console.log(`Hedera ledger sidecar listening on :${port}`));
