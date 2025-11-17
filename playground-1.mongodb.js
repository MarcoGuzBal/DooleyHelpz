// Connects to your current cluster context
use("DooleyHelpz");

// Create the collection and insert a test document
db.createCollection("courses_detailed");
db.courses_detailed.insertOne({ "_healthcheck": "ok" });

// Verify
db.getCollectionNames();

