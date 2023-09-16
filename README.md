# RealistikGDPS
The Python-based backend for RealistikGDPS, made as an expandable solution for a GDPS of any size.

## What is this?
This is a modern Python implementation of the Geometry Dash server protocol meant to power my Geometry Dash Private server.
It is written in asynchronous, modern Python and is meant as a replacement for our current [PHP based infrastructure](https://github.com/Cvolton/GMDprivateServer).

## Interesting Features
- Fully Dockerised, allowing for easy setup
- MeiliSearch, allowing for typo tolerance
- S3 support, allowing for flexible storage solutions
- Proper ratelimiting
- Kubernetes support

## How to set up?
- Ensure Docker and Make are installed on your system.
- Create a copy of the `.env.example` file named `.env` and adjust it to your liking.
- Run `make build` to build the RealistikGDPS image.
- Run `make run` to run everything.

TODO: Non-docker setup instructions.

You may use environment variables (no `.env` file support yet) for config by setting the `USE_ENV_CONFIG` variable to "1".

## Configuration
As previously mentioned, RealistikGDPS currently supports two ways of configuring the server.

### Using Docker (compose)
The Docker configuration process is by far the simplest as it includes all services in one.

- Create a copy of `.env.example` named `.env`
This creates a copy of the default config with all the field names ready for editing.

- Edit the `.env` file to your liking
Due to the all-in-one nature of Docker, the defaults are unlikely to require any changing with the exception
`SRV_NAME`, representing the name of your GDPS.

### Without Docker
Configuring a bare instance of RealistikGDPS requires more work as you are responsible for setting up the services
(such as MySQL and Redis). This means that the majority of the configuration is setup dependent.

By default, RealistikGDPS will generate a `config.json` file on first run that you are able to edit with all the fields present.
Equally, you may select to use environment variables for configuration if the `USE_ENV_CONFIG` var is set to "1".

Both methods accept the same values (identical names).

## Upgrading an existing server
Assuming your server is based off [Cvolton's server implementation](https://github.com/Cvolton/GMDprivateServer), there will be a migration utility created in the near future.
