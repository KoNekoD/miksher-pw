import json
import subprocess
import time
from typing import List

from pipewire_python import link
from pipewire_python.link import StereoInput, StereoOutput


def create_virtual_microphone(name="VirtualMicrophone"):
    """
    Create a virtual microphone for PipeWire.
    """
    try:
        # Load the null sink (virtual audio sink)
        sink_module = subprocess.run(
            ["pactl", "load-module", "module-null-sink", f"sink_name={name}"],
            stdout=subprocess.PIPE,
            check=True,
        ).stdout.decode("utf-8").strip()

        print(f"Virtual sink '{name}' created with module ID: {sink_module}")

        # Verify the sink creation using pactl list sinks
        sinks_output = subprocess.run(
            ["pactl", "-f", "json", "list", "sinks"],
            stdout=subprocess.PIPE,
            check=True,
        ).stdout.decode("utf-8")
        sinks = json.loads(sinks_output)

        sink_node = None
        for sink in sinks:
            if sink["name"] == name:
                sink_node = sink["index"]
                break

        if sink_node is None:
            raise RuntimeError("Failed to find the virtual sink node.")

        print(f"Sink node found with ID: {sink_node}")

        # Link the virtual sink to a source (loopback)
        # source_module = subprocess.run(
        #     [
        #         "pactl",
        #         "load-module",
        #         "module-loopback",
        #         f"source={name}.monitor",
        #         f"sink={name}",
        #     ],
        #     stdout=subprocess.PIPE,
        #     check=True,
        # ).stdout.decode("utf-8").strip()
        #
        # print(f"Loopback source created with module ID: {source_module}")
        print(f"Virtual microphone '{name}' setup successfully.")

    except subprocess.CalledProcessError as e:
        print(f"Error occurred while setting up virtual mic: {e}")
    except Exception as ex:
        print(f"Unexpected error: {ex}")


def delete_virtual_microphone(name="VirtualMicrophone"):
    """
    Delete a virtual microphone created with PipeWire.
    """
    try:
        # List all loaded modules
        modules_output = subprocess.run(
            ["pactl", "-f", "json", "list", "modules"],
            stdout=subprocess.PIPE,
            check=True,
        ).stdout.decode("utf-8")
        modules = json.loads(modules_output)

        modules_to_unload = []

        # Find all modules related to the given name
        for module in modules:
            if module["argument"] is None:
                continue
            argument = module["argument"]

            splittable_char_count = argument.count("=")

            if splittable_char_count == 0:
                continue

            if splittable_char_count == 1:
                split_argument = argument.split("=")
                if split_argument[1] == name:
                    modules_to_unload.append(module["name"])
            else:
                split_arguments = argument.split(" ")
                for split_argument_item in split_arguments:
                    split_argument = split_argument_item.split("=")
                    if len(split_argument) == 2 and split_argument[1] == name:
                        modules_to_unload.append(module["name"])

        if not modules_to_unload:
            print(f"No modules found for virtual microphone '{name}'.")
            return

        # Unload all related modules
        for module_id in modules_to_unload:
            subprocess.run(["pactl", "unload-module", str(module_id)], check=True)
            print(f"Unloaded module ID: {module_id}")

        print(f"Virtual microphone '{name}' successfully deleted.")

    except subprocess.CalledProcessError as e:
        print(f"Error occurred while deleting virtual mic: {e}")
    except Exception as ex:
        print(f"Unexpected error: {ex}")


def get_mic_list() -> List[StereoInput]:
    inputs = link.list_inputs()
    mic_list = []
    for sink in inputs:
        if not isinstance(sink, StereoInput):
            continue
        if sink.left.device == 'alsa_output.pci-0000_00_1f.3.analog-stereo':
            continue
        if sink.left.name != 'input_FL':
            continue

        mic_list.append(sink)

    return mic_list


def pw_dump():
    res = subprocess.run(
        ["pw-dump"],
        stdout=subprocess.PIPE,
        check=True,
    ).stdout.decode("utf-8").strip()

    json_decoded = json.loads(res)

    links_list = []

    for item in json_decoded:
        if item['type'] != 'PipeWire:Interface:Link':
            continue

        links_list.append({'input': item['info']['input-port-id'], 'output': item['info']['output-port-id']})

    return links_list


def get_outputs_list(mic_names_list: List[str]) -> List[StereoOutput]:
    outputs = link.list_outputs()
    outputs_list = []
    for source in outputs:
        if not isinstance(source, StereoOutput):
            continue
        if source.left.device in mic_names_list:
            continue
        if source.left.device == 'alsa_output.pci-0000_00_1f.3.analog-stereo':
            continue
        if source.left.name != 'output_FL':
            continue

        outputs_list.append(source)

    return outputs_list


def is_do_not_needed_link(mic: StereoInput, out: StereoOutput):
    links_list = pw_dump()

    for link_item in links_list:
        if link_item['input'] == int(mic.left.id) and link_item['output'] == int(out.left.id):
            return True

    return False


def check_update():
    mic_list = get_mic_list()

    if len(mic_list) == 0:
        print("[X] No microphone found")
        return

    mic_list_names = [mic.left.device for mic in mic_list]

    outputs_list = get_outputs_list(mic_list_names)

    for out in outputs_list:
        for mic in mic_list:
            try:
                if is_do_not_needed_link(mic, out):
                    print(f"||> Skip connecting {out.left.device} to {mic.left.device}")
                    continue
                out.connect(mic)
                print(f"|> Connected {out.left.device} to {mic.left.device}")
            except Exception as e:
                print(f"[X] Failed to connect {out} to {mic}: {e}")


if __name__ == '__main__':
    while True:
        print("\n\n\n\n\n\n\n\n\n\nChecking for updates...")

        check_update()

        time.sleep(5)
