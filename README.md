# vericheck-fact-verification-platform-211511-211520

Backend MongoDB configuration notes:

- Prefer setting MONGO_URI and MONGO_DB. If MONGO_URI is missing or malformed, the backend attempts to build it from MONGO_HOST, MONGO_PORT, MONGO_USER, MONGO_PASSWORD, and MONGO_DB.
- Do not include trailing commas in the host list. Trailing commas cause "ConfigurationError: Empty host".
  - Single host: mongodb://localhost:27017
  - Replica set: mongodb://host1:27017,host2:27017,host3:27017/?replicaSet=rs0
- The application logs the effective host and database at startup without revealing the password.
- See fact_checking_backend/.env.example for a working template.