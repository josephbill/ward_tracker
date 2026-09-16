/**
 * One-time setup: creates the HCS topic that every report event gets
 * anchored to, and prints its id to paste into .env as HEDERA_TOPIC_ID.
 *
 *   npm run create-topic
 */
require("dotenv/config");
const { TopicCreateTransaction } = require("@hashgraph/sdk");
const { getClient } = require("./hedera");

async function main() {
  const client = getClient();
  const tx = await new TopicCreateTransaction()
    .setTopicMemo("County Ward Tracker — citizen report audit trail (PoC)")
    .execute(client);
  const receipt = await tx.getReceipt(client);
  console.log(`Created topic: ${receipt.topicId.toString()}`);
  console.log("Paste this into ledger-sidecar/.env as HEDERA_TOPIC_ID");
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
