# SEMIS - Stable Economic Modular Illumination Setup

![SEMIS](Resources/SEMIS.png)

## Table of Contents
- [Introduction](#introduction)
    - [Folder structure](#folder-structure)
- [For users](#for-users)
- [For developers](#for-developers)

## Introduction
SEMIS is a solar simulator specifically designed for perovskite cell stability testing.

Key advantages:
- Price: low-cost enables scalability of experiments
- Modularity: high repairability and ease of integration
- Durability: LED technology enables long-lifetime ~ 20 000 hours
- Simplicity: easy to control and modify the system

### Folder structure

| Folder      | Description |
| ----------- | ----------- |
| /Documentation      | Literature research, reports, and presentations       |
| /Hardware   | CAD designs and hardware datasheets        |
| /Software   | SEMIS controller and software used for testing        |
| /Resources   | Graphics used in the documentation   |

## For users

### Safety considerations

<font color="orange">Please read these instructions carefully.</font> Failing to do so can result in severe harm to the user and people in the surroundings.

- SEMIS is a solar simulator, which means that its output radiation intensity is comparable to that of the sun. <font color="red">Avoid direct eye exposure.</font> <font color="green">Wear eye protection (e.g. sunglasses).</font> Prolonged exposure on undesired areas (e.g. skin) might also have a negative impact. Since part of the spectrum is not in the visible range, **turn off and unplug the device** before any inspection.
- Avoid illuminating **reflective surfaces**. Light reflected back to the light source can contribute to overheating of the device and lead to malfunction. Light reflected to the surroundings could cause undesired exposure.
- SEMIS contains high voltage elements <font color="red">(up to 36V of electrical potential).</font> **Do not alter any components while the device is plugged.** 
- **Recommended operating conditions:** <font color="green">25&deg; and 70% RH, or lower</font>.

### Instructions for use
#### Setup
1. Before powering the device, attach it firmly to a solid table. 
2. Make sure that the target illuminated surface is **NOT reflective** (e.g., a mirror). If light is reflected back to the source, it can cause damage to the system or people in the surroundings.
3. Prepare your sample holder, i.e., where the device under test (DUT) will be mounted for exposure to the output of SEMIS. Adjust the height of SEMIS until the DUTs are directly at the end of the reflector of SEMIS (less than a centimeter away.).
4. Remove any devices from the illuminated surface.
5. Plug the device and turn it on with the switch in the power box. 
6. The fans should start automatically. If this is **not** the case, <font color="orange">switch off and unplug the device.</font> It is **not** safe to use the device without the cooling system. Check the [troubleshooting](#troubleshooting) section.
7. The light output is set to 50% on startup. The device can be controlled via Wi-Fi. With a Wi-Fi capable device (e.g., a phone), find the network "SEMIS_#_AP". Connect and find the IP address. Insert the IP in a browser. The controller should be shown as below.

<img src="Resources/SS_controller_UI.png" alt="SEMIS controller" width="400">


#### Calibration

// TODO

#### After use

12. Switch off SEMIS.
13. Unplug from the wall.



## For developers

<font color="orange">Please check the [Safety Considerations](#safety-considerations).</font>

### Building SEMIS

This instruction is still a **work in progress**, due to the continuous development of SEMIS. Building is therefore **only recommended for experienced professionals**.

A detailed description of SEMIS, its part list, and information about its components is described in the [report](/Documentation/Report_03_2026_Alejandro_Guzman.pdf), inside the [Documentation](/Documentation) folder. Important remarks:

- Mechanical considerations: 
    - Most of the mechanical components are 3D printed or hand-made. Pay close attention to the dimensions shown in the appendix **"Assembly Drawings"** of the [report](/Documentation/Report_03_2026_Alejandro_Guzman.pdf). The last drawing in that section contains assembly instructions and a list of additional parts for assembly (e.g. nuts and screws).
    - 3D files for printing are provided in the folder [Hardware](/Hardware/Structure%20CAD)

- Electrical considerations: 
    - Circuit diagrams are in appendix **"Power and control considerations"** of the [report](/Documentation/Report_03_2026_Alejandro_Guzman.pdf). 
    - Wire everything properly **before** plugging the device.
    - Ensure all wires and electric contacts are properly insulated.
    - Wiring the **Fans** has not been documented yet. <font color="red">It is **not** safe to use SEMIS without a cooling.</font> Make sure to at least blow some air on top of the light sources with a fan to improve heat dissipation.
    - If using alternative LEDs, make sure the electric characteristics of all components are compatible. 

- Software/Hardware dependencies: 
    - For control, DACs are used and programmed for a specific model (MCP4802). Compatibility of the components must be ensured. **Please check datasheets of the respective components.**


### Modifying SEMIS

// TODO

### Integrating SEMIS into other systems

// TODO

## Troubleshooting

### Fans not working

If the fans are not working properly, it is necessary to check electrical connections and the components. The fans work all the time while the device is powered.

### Additional resources

Feel free to contact me: [Alejandro Guzmán](mailto:alejandroguzt@gmail.com)

