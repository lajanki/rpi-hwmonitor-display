# rpi-hwmonitor-display
A system hardware status monitor displaying host system's CPU, RAM and GPU statistics on a Raspberry Pi client. Host can be a Linux or a Windows system. Message delivery between host and client is based on Google Pub/Sub.

[![Unit tests](https://github.com/lajanki/rpi-hwmonitor-display/actions/workflows/run-tests.yml/badge.svg?branch=main)](https://github.com/lajanki/rpi-hwmonitor-display/actions/workflows/run-tests.yml)

System statistics monitored include:
 * :computer: CPU utilization
   * System-wide percentage of CPU in use
   * 1 minute load average
   * Number of cores with utilization > 50%
   * Individual cpu core utilization
 * :thermometer: CPU and GPU overall utilization and temperatures
 * :bar_chart: GPU and total system RAM usage

> [!NOTE]  
> Only Nvidia GPUs are supported
 

![Main window](hwmonitor.png)


## Google Cloud Setup
To setup the Google Cloud infrastructure you need:
 * a [Google Cloud project](https://cloud.google.com/) with Pub/Sub enabled.
 * [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) with `gcloud` command line tool.

Then create the a topic with a subscription and a service account using `setup_pubsub.sh`:
 * fill `.template_env` with your project id and names for your Pub/Sub topic and subscription.
 * Rename the file to `.env`.
 * Source the file and create the related resources with
    ```shell
    source .env
    ./setup_pubsub.sh
    ```
This will also download a json key for the service account to `~/Downloads`. This can be used as an authentication method from Raspberry Pi by setting
the `GOOGLE_APPLICATION_CREDENTIALS` env variable (it can be added to your `.env` file).
 * https://cloud.google.com/docs/authentication/application-default-credentials



## Python setup - Linux
Install dependencies with
```shell
pip install -r requirements.txt
```

## Run
Run the statistics poller on the host system with:
```shell
python poller.py
```
Then, run the monitor on the client (or in a different terminal) with
```shell
python main.py
```

## Windows setup
Running the poller on Windows requires some additional preparations. The library used to poll CPU statistics on Linux, `psutil`, has limited functionality on Windows. In order to retain it, polling on Windows relies on a 3rd party software, [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor). Download the monitor and run it in the background. Having it automatically start on Windows startup is recommended.

Next, install Windows only dependencies with
```shell
pip install -r requirements-win.txt
```

You can now run `poller.py` with the above command.


## Poller configuration and Pub/Sub pricing
Polling frequency can be adjusted in `.env`. If not set, a default value of 5 will be used which means statistics are polled, and a message is published to the Pub/Sub topic every 5 seconds.

Pub/Sub's [pricing](https://cloud.google.com/pubsub/pricing) is based on data sent with a minimum of 1000 bytes per publish. Actual data published is around 600kB. Thus, publishing and receiving a message every 5 seconds (12 times per minute) transmit a total of `12 * 2kB = 24kB` per minute. Running both the poller and the monitor constantly would then transmit `24 * 60 * 24kB = 34560kB ~ 35MB` per day, roughly `1 GB / month`. 

There is a free tier where the first 10 gigabytes of usage each month are free.

## Unit tests
Unit tests can be run with:
```shell
pytest
```