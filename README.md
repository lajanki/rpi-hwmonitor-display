# rpi-hwmonitor-display
A client-server model system hardware status monitor.

![Main window](hwmonitor.png)


[![Unit tests](https://github.com/lajanki/rpi-hwmonitor-display/actions/workflows/run-tests.yml/badge.svg?branch=main)](https://github.com/lajanki/rpi-hwmonitor-display/actions/workflows/run-tests.yml)

Displays client system's CPU, (Nvidia) GPU and memory usage statistics on a separate server device. Built with a Raspberry Pi as the server.

Hardware readings are periodically collected from the client and sent to the server via a TCP socket over a local network.

System statistics monitored include:
 * Current CPU utilization :computer:
   * Overall CPU utilization percentage
   * 1 minute load average
   * Number of cores with high utilization
   * Individual CPU core utilization
 * CPU and GPU utilization graphs :chart_with_upwards_trend:
 * CPU and GPU temperatures :thermometer:
 * GPU and total system RAM usage :bar_chart:

> [!NOTE]  
> Only Nvidia GPUs are supported
 


## Setup
To setup the network connection, add the server system's (the monitor) local IP address or hostname to `config.tmpl.toml`
and rename the file to `config.toml`. Optionally, the TCP port number can also be configured. 

### Python setup
Install dependencies with
```shell
pip install -r requirements.txt
```

### Note in PyQt5 installation
The user interface is based on the Qt framework (version 5). Installing the Python bindings for `PyQt5` can be a bit challenging,
particuarly for on a Raspberry Pi as it has to be compiled from source. Building from the source includes a hidden
prompt for accepting its GPL license. The above pip install command may hang, and eventually be killed, due to this step.

To pass this prompt, install PyQt5, and its dependencies, with:

```shell
pip -v install --config-settings --confirm-license= PyQt5
```
See,
https://www.riverbankcomputing.com/static/Docs/PyQt5/installation.html#installing-the-gpl-version
for more information.

> [!NOTE]  
> On an older Raspberry Pi model this may take several hours!


## Run
First, start the monitor process on the server with:
```shell
python main.py
```

Then, run the statistics poller on the client (or sinply from another terminal window) with:
```shell
python poller.py
```

![Network](network.drawio.png)


## Note on Windows setup
Running the poller on Windows requires some additional preparations. The library used to poll CPU statistics on Linux,
`psutil`, has limited functionality on Windows. In order to retain it, polling on Windows relies on a 3rd party tool,
[LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor).
Download the monitor and run it in the background.
Having it automatically start on Windows startup is recommended.

Then, install Windows only dependencies with
```shell
pip install -r requirements-win.txt
```

You can now run `poller.py` with the above command.

## Unit tests
Unit tests can be run with:
```shell
pytest
```


## Legacy: Running on Google Cloud infrastructure
An alternative transport mechanism is avialble for passing the hardware readings to the server: Google Cloud Pub/Sub.
However, this is a legacy solution requiring more setup and offering no real benefit over a local network.
It can be useful when the client and the server are not in the same network.

To setup the Google Cloud infrastructure you need:
 * a [Google Cloud project](https://cloud.google.com/) with Pub/Sub enabled.
 * [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) with `gcloud` command line tool.

Then create the a topic with a subscription and a service account with the setup script `extras/setup_pubsub.sh`:
```shell
cd extras
./setup_pubsub.sh
```

This will also download a json key for the service account and set the `GOOGLE_APPLICATION_CREDENTIALS`
env variable in `extras/.env` which will be used to auhenticate to Google Cloud.
 * https://cloud.google.com/docs/authentication/application-default-credentials


To run the poller and the server using Pub/Sub as transport, pass `--transport Pub/Sub` as an argument to both
files.


### Pub/Sub pricing
Pub/Sub's [pricing](https://cloud.google.com/pubsub/pricing) is (mostly) based on throughput (data published to and read from a topic).

A single message published is around `500B`. However, Pub/Sub will process a minimum of `1 000B` per call
 * https://cloud.google.com/pubsub/quotas#throughput_quota_units

Thus, running the poller and monitor constantly for 24 hours with the default refresh interval of 2 seconds
(ie. 43 200 messages) will process a total of `43 200 * 2 * 1kB = 86 400kB ~ 84MB`

There is a free tier where the first `10GiB` of throughput is free each month.
