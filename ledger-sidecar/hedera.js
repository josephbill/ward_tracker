/**
 * Thin wrapper around the Hedera Consensus Service (HCS) calls this sidecar
 * needs: submit one message (a payload hash) to the configured topic, and
 * re-derive a receipt's consensus timestamp for verification.
 *
 * Not exercised in this PoC without real HEDERA_OPERATOR_ID/KEY/TOPIC_ID —
 * see ../docs/ARCHITECTURE.md for what's real vs stubbed. The Python side
 * (app/services/ledger/stub_client.py) mirrors this exact shape so swapping
 * LEDGER_BACKEND=hedera_sidecar in the Flask config is the only change
 * needed once credentials exist.
 */
const {
  Client,
  TopicMessageSubmitTransaction,
  TopicMessageQuery,
  PrivateKey,
} = require("@hashgraph/sdk");

function getClient() {
  const network = process.env.HEDERA_NETWORK || "testnet";
  const operatorId = process.env.HEDERA_OPERATOR_ID;
  const operatorKey = process.env.HEDERA_OPERATOR_KEY;

  if (!operatorId || !operatorKey) {
    throw new Error(
      "HEDERA_OPERATOR_ID / HEDERA_OPERATOR_KEY are not set. Copy .env.example to " +
        ".env and fill in real testnet credentials from https://portal.hedera.com/ " +
        "before starting the sidecar with LEDGER_BACKEND=hedera_sidecar."
    );
  }

  const key = PrivateKey.fromString(operatorKey);
console.log("Derived public key:", key.publicKey.toString());
  const client = network === "mainnet" ? Client.forMainnet() : Client.forTestnet();
  client.setOperator(operatorId, PrivateKey.fromString(operatorKey));
  return client;
}

async function submitEvent(eventType, payloadHash) {
  const topicId = process.env.HEDERA_TOPIC_ID;
  if (!topicId) {
    throw new Error("HEDERA_TOPIC_ID is not set — run `npm run create-topic` first.");
  }

  const client = getClient();
  const message = JSON.stringify({ event_type: eventType, payload_hash: payloadHash });

  const tx = await new TopicMessageSubmitTransaction({ topicId, message }).execute(client);
  const receipt = await tx.getReceipt(client);

  // ledger_ref encodes topic + sequence number so it can be looked up again
  // for verification (via a mirror-node query, see verifyEvent below).
  return {
    ledger_ref: `${topicId}/${receipt.topicSequenceNumber.toString()}`,
    transaction_id: tx.transactionId.toString(),
  };
}

/**
 * Verification uses the free Hedera mirror-node REST API rather than the
 * consensus-node SDK, since mirror nodes are built exactly for "look up a
 * past message by topic+sequence" queries like this one.
 */
async function verifyEvent(payloadHash, ledgerRef) {
  const [topicId, sequenceNumber] = ledgerRef.split("/");
  const network = process.env.HEDERA_NETWORK || "testnet";
  const mirrorBase =
    network === "mainnet"
      ? "https://mainnet-public.mirrornode.hedera.com"
      : "https://testnet.mirrornode.hedera.com";

  const url = `${mirrorBase}/api/v1/topics/${topicId}/messages/${sequenceNumber}`;
  const resp = await fetch(url);
  if (!resp.ok) return false;

  const data = await resp.json();
  const decoded = JSON.parse(Buffer.from(data.message, "base64").toString("utf-8"));
  return decoded.payload_hash === payloadHash;
}

module.exports = { getClient, submitEvent, verifyEvent };
