<div align="center">
  <img src="images/kherimoyasingle665.png" alt="kherimoya" width="300"/> <img src="images/kherimoya.png" alt="kherimoyafolder" width="90"/>

  /kɛrɪˈmoʊjə/ care-ih-moh-ya

# Kherimoya - Minecraft Bedrock Server Management Through [Endstone](https://github.com/EndstoneMC/endstone)
</div>

> [!WARNING]
> Kherimoya is still in its **early development stages**, which means that it's not in the best state right now. I wouldn't recommend Kherimoya yet as it doesn't offer enough features.

> [!NOTE]
> I haven't really tested the TUI, because I cannot with what I have right now (my laptop has broken and I'm still waiting on it to be fixed, I've only been working on Kherimoya through Github codespaces on this Android tablet, limiting me by a lot. When it's fixed, I'll work on it myself more)

## introduction
Kherimoya is a Minecraft Bedrock server management tool which uses [Endstone](https://github.com/EndstoneMC/endstone), meant for people who host a lot of servers *(a great example for a use case right now would be for a minecraft bedrock server hosting service)*.

In the future, Kherimoya will soon provide WAY more features in the form of Kherimoya+, an extension that adds on to Kherimoya with way more features, seperated from Kherimoya to keep it lightweight.

## features

## planned features
The following features <strong>WILL</strong> be included in Kherimoya in the future.
<ul>
    <li>Documentation
    <li>Kherimoya endstone plugin, that can do things like tell the status of the server and communicate with Kherimoya
    <li><s>More features like server status, discord bot, etc... (discord bot may just become extension)</s> <i>(Features like this will be a part of Kherimoya+.)</i>
    <li>Automatic server backups
    <li>Extensions
</ul>
The following features <strong>MAY</strong> be includeded in Kherimoya in the future
<ul>
    <li>Custom API for Endstone plugins
    <li><s>Native Windows compatability</s> <i>Use WSL, This is because Kherimoya will heavily relies on tmux</i>
</ul>

Kherimoya **will** be mostly just a backend for server management. This means you could make your own UI's, and modify it to however extent you want

## setup

<details>
<summary>Linux</summary>

<details>
<summary>Prerequisites</summary>

- python (3.9+)

- git

- tmux
</details>

1. Clone the repository & CD into it

```bash
git clone https://github.com/niko-at-chalupa/kherimoya && cd kherimoya
```

2. Create a virtual environment & activate it
```bash
python -m venv venv && source venv/bin/activate
```

3. Install packages
```bash
pip install -r requirements.txt
```
</details>

## usage
Run `simple_tui.py` to use Kherimoya's built-in UI, or make your own interface *(documenation soon)*

```bash
python3 simple_tui.py # Make sure you're in the correct Python environment, and you're inside Kherimoya's project directory
```