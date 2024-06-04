# RealistikGDPS
The Python-based backend for RealistikGDPS, made as an expandable solution for a GDPS of any size.

For support and a public running instance, please visit [our Discord!](https://discord.gg/uNTPGPn3D5)

## What is this?
This is a modern Python implementation of the Geometry Dash server protocol meant to power my Geometry Dash Private server.
It is written in asynchronous, modern Python and is meant as a replacement for our current [PHP based infrastructure](https://github.com/Cvolton/GMDprivateServer).

## Interesting Features
- Fully Dockerised, allowing for easy setup
- MeiliSearch, allowing for typo tolerance
- S3 support, allowing for flexible storage solutions
- Proper ratelimiting
- Flexible command framework

## How to set up?
- Ensure Docker and Make are installed on your system.
- Create a copy of the `.env.example` file named `.env` and adjust it to your liking.
- Run `make build` to build the RealistikGDPS image.
- Run `make run` to run everything.

TODO: Non-docker setup instructions.

## Configuration
As previously mentioned, RealistikGDPS currently supports two ways of configuring the server.
In both cases the configuration is done through the `.env` file.

- Create a copy of `.env.example` named `.env`
This creates a copy of the default config with all the field names ready for editing.

- Edit the `.env` file to your liking
Due to the all-in-one nature of Docker, the defaults are unlikely to require any changing with the exception
`SRV_NAME`, representing the name of your GDPS.

## Upgrading an existing server
Assuming your server is based off [Cvolton's server implementation](https://github.com/Cvolton/GMDprivateServer), there exists a migration
utility for this built right into the codebase.

This is done by importing your old database into a database named `old_gdps` and running `make converter` (assuming you are using Docker).
This will fill **all empty** tables with data from the old table.
