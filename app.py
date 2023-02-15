"""
A MIDI inter-connector.
"""

import hashlib
import re
import threading
import time
from collections import defaultdict
from typing import Dict, Optional, Set, Tuple

import mido
import pygame
from pygame._sdl2 import touch


DEVICE_POLL = 1
IGNORED_DEVICES = {"Midi Through Port", "RtMidi"}

# from https://sashamaps.net/docs/resources/20-colors/
COLORS = [
    "#e6194b",
    "#3cb44b",
    "#ffe119",
    "#4363d8",
    "#f58231",
    "#911eb4",
    "#46f0f0",
    "#f032e6",
    "#bcf60c",
    "#fabebe",
    "#008080",
    "#e6beff",
    "#9a6324",
    "#fffac8",
    "#800000",
    "#aaffc3",
    "#808000",
    "#ffd8b1",
    "#000075",
    "#808080",
    "#ffffff",
    "#000000",
]


def update_ports(
    inputs: Dict[str, Optional[mido.ports.BaseInput]],
    outputs: Dict[str, Optional[mido.ports.BaseOutput]],
    connections: Dict[str, Set[str]],
) -> None:
    """
    Periodically poll for devices.
    """
    while True:
        new_inputs = {
            name
            for name in mido.get_input_names()
            if all(device not in name for device in IGNORED_DEVICES)
        }
        for removed in set(inputs) - new_inputs:
            del inputs[removed]
            if removed in connections:
                del connections[removed]
        for added in new_inputs - set(inputs):
            inputs[added] = None

        new_outputs = {
            name
            for name in mido.get_output_names()
            if all(device not in name for device in IGNORED_DEVICES)
        }
        for removed in set(outputs) - new_outputs:
            del outputs[removed]
            for targets in connections.values():
                if removed in targets:
                    targets.remove(removed)
        for added in new_outputs - set(outputs):
            outputs[added] = None

        time.sleep(DEVICE_POLL)


def main() -> None:  # pylint: disable=too-many-locals
    """
    Main loop.
    """
    pygame.init()

    font = pygame.font.SysFont(None, 24)
    screen = pygame.display.set_mode([800, 480])
    width, height = screen.get_size()
    # screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

    inputs: Dict[str, Optional[mido.ports.BaseInput]] = {}
    outputs: Dict[str, Optional[mido.ports.BaseOutput]] = {}
    connections = defaultdict(set)
    thread = threading.Thread(
        target=update_ports,
        args=(inputs, outputs, connections),
    )
    thread.start()

    done = False
    clock = pygame.time.Clock()
    while not done:
        drag_start = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True
            if event.type == pygame.MOUSEBUTTONDOWN:
                drag_start = pygame.mouse.get_pos()
            if event.type == pygame.MOUSEBUTTONUP:
                drag_end = pygame.mouse.get_pos()
                handle_connection(
                    screen,
                    drag_start,
                    drag_end,
                    inputs,
                    outputs,
                    connections,
                )
                drag_start = None

        # propagate messages
        for source, targets in connections.items():
            if inputs[source] is None:
                inputs[source] = mido.open_input(source)
            for message in inputs[source].iter_pending():
                for target in targets:
                    if outputs[target] is None:
                        outputs[target] = mido.open_output(target)
                    outputs[target].send(message)

        # draw UI
        draw_ports(screen, font, inputs, 0)
        draw_connections(screen, inputs, connections)
        draw_ports(screen, font, outputs, width / 2)
        pygame.draw.line(screen, "black", (width / 2, 0), (width / 2, height))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


def handle_connection(  # pylint: disable=too-many-arguments, too-many-locals
    screen: pygame.Surface,
    drag_start: Tuple[float, float],
    drag_end: Tuple[float, float],
    inputs: Dict[str, Optional[mido.ports.BaseInput]],
    outputs: Dict[str, Optional[mido.ports.BaseOutput]],
    connections: Dict[str, Set[str]],
) -> None:
    """
    Connect or disconnect ports.
    """
    width, height = screen.get_size()
    start_x, start_y = drag_start
    end_x, end_y = drag_end

    # no connection
    if (start_x < width / 2 and end_x < width / 2) or (
        start_x > width / 2 and end_x > width / 2
    ):
        return

    if start_x < width / 2:
        input_y, output_y = start_y, end_y
    else:
        input_y, output_y = end_y, start_y

    input_ = (len(inputs) * height) // input_y
    output = (len(outputs) * height) // output_y

    if output in connections[input_]:
        connections[input_].remove(output)
    else:
        connections[input_].add(output)


def draw_ports(
    screen: pygame.Surface,
    font: pygame.font.SysFont,
    ports: Set[mido.ports.BasePort],
    x_offset: int,
) -> None:
    """
    Draw all ports at a given x offset (0 for inputs, half width for outputs).
    """
    width, height = screen.get_size()

    for i, name in enumerate(sorted(ports)):
        short_name = re.sub(r".*?:(.*?)\d+:\d+", r"\1", name)
        color_index = int(hashlib.md5(name.encode()).hexdigest(), 16)
        color = COLORS[color_index % len(COLORS)]
        y_pos = i * height / len(ports)
        pygame.draw.rect(
            screen, color, [x_offset, y_pos, width / 2, height / len(ports)]
        )
        pygame.draw.rect(
            screen,
            "black",
            [x_offset, y_pos, width / 2, height / len(ports)],
            1,
        )
        text = font.render(short_name, True, (0, 0, 0))
        text_rect = text.get_rect(
            center=(width / 4, y_pos + (height / (2 * len(ports))))
        )
        screen.blit(text, text_rect)


def draw_connections(screen, inputs, connections) -> None:
    """
    Draw connections on the input boxes.
    """
    width, height = screen.get_size()

    for i, name in enumerate(sorted(inputs)):
        for j, target in enumerate(sorted(connections[name])):
            cell_height = (height / len(inputs)) / len(connections[name])
            color_index = int(hashlib.md5(target.encode()).hexdigest(), 16)
            color = COLORS[color_index % len(COLORS)]
            x_pos = (width / 2) - 20
            y_pos = (i * height / len(inputs)) + (j * cell_height)
            pygame.draw.rect(screen, color, [x_pos, y_pos, 20, cell_height])
            pygame.draw.rect(screen, "black", [x_pos, y_pos, 20, cell_height], 1)


if __name__ == "__main__":
    main()
