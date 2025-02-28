# Installing Python 3.9 for EEGPT Package

The EEGPT package requires Python 3.9. If Python 3.9 is not installed, follow the steps below. 
If Python 3.9 is already installed, skip to the section on creating a Python environment at a custom path.

---

## **Install Python 3.9**

### 1. Update the Package List
Ensure your package list is up to date:
```bash
sudo apt update
```

### 2. Install Python 3.9
Install Python 3.9 and its package manager (`pip`):
```bash
sudo apt install python3.9 python3.9-distutils
```

### 3. Install Pip for Python 3.9
If `pip` is not installed, download and install it:
```bash
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python3.9 get-pip.py
```

### 4. Install Python 3.9 Development Headers
Install the development headers required for compiling Python extensions:
```bash
sudo apt install python3.9-dev
```

### 5. Install Ninja Build System
Install `ninja` for faster builds:
```bash
sudo apt install ninja-build
```

### 6. Verify Installation
Check that Python 3.9, `pip`, and `ninja` are installed correctly:
```bash
python3.9 --version
pip --version
ninja --version
```

### 7. Upgrade Pip and Setuptools
Ensure `pip` and `setuptools` are up to date:
```bash
python3.9 -m pip install --upgrade pip setuptools
```

---

## **Link Python 3.9 to `python` (Optional)**

If you want to use `python3.9` as the default `python` command, create a symbolic link:

1. Check the current `python` version:
   ```bash
   python --version
   ```

2. Remove the existing `python` link (if any):
   ```bash
   sudo rm /usr/bin/python
   ```

3. Create a symbolic link to `python3.9`:
   ```bash
   sudo ln -s /usr/bin/python3.9 /usr/bin/python
   ```

4. Verify the link:
   ```bash
   python --version
   ```

---

## **Create an Isolated Python Environment**

To create an isolated Python environment at a custom address (e.g., `/mnt/d/python/envs/EEGPT_env`), use the following command:

```bash
python3.9 -m venv /mnt/d/python/envs/EEGPT_env
```

Activate the environment:
```bash
source /mnt/d/python/envs/EEGPT_env/bin/activate
```

Deactivate the environment when done:
```bash
deactivate
```

## **Install needed dependencies from requirements.txt**

First activate the environment and then navigate to where EEGPT pacakge is installed and run the following command.
```bash
pip install -r requirements.txt
```

Use the following to Ignore dependencies and install exact versions in the requirement file
```bash
pip install --no-deps -r requirements.txt
```

Use the following to chech if there are any unresolved conflicts
```bash
pip check
```

---

This guide ensures Python 3.9 is installed, configured, and ready for use with the EEGPT package. Let me know if you need further assistance!