# Product

<!-- impeccable:product-schema 1 -->

## Platform

Windows desktop

## Users

The primary user is a Windows PC owner who wants to use an iPhone microphone as a live input for communication and recording apps.

## Product Purpose

MicUSB carries iPhone microphone audio over USB to Windows, applies voice processing, and sends it to VB-Cable so desktop apps can select it as their microphone.

## Positioning

The audio reaches the PC through the USB device tunnel; voice processing runs locally on the PC.

## Operating Context

The user runs MicUSB alongside the iPhone app and selects CABLE Output in desktop software such as Discord, OBS, or Zoom. The Windows app can stay in the notification area while audio continues.

## Capabilities and Constraints

- Controls include microphone gain, automatic gain, background gate, tone softening, DeepFilterNet3 noise reduction, and a low frequency filter.
- iPhone microphone source selection is exposed when iOS provides selectable built-in input sources.
- Audio is processed locally at 48 kHz mono and routed to VB-Cable.
- A free Apple developer account may require periodic IPA reinstall through Sideloadly.
- The Windows desktop UI is implemented in Python and Tkinter; startup, minimize-to-tray, and tray exit behavior must remain available.

## Brand Commitments

The user requests a black, premium interface with restrained gray/black title-bar controls and an Apple-influenced level of finish. Do not imply Apple affiliation or use Apple's logo.

## Evidence on Hand

The application source, workflow, and user-confirmed operating steps are present in this repository. No independent audio quality measurements or latency guarantees have been established.

## Product Principles

- Keep the live audio path easy to understand.
- Keep signal controls responsive while audio is running.
- Make connection and processing state legible at a glance.
- Keep the app accessible from the Windows notification area.
