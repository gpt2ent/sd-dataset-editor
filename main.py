from nicegui import ui
import os
import numpy as np
import base64

async def toggle_dark(x):
    js_value = str(x.value).lower()
    await ui.run_javascript(f'Quasar.Dark.set({js_value})', respond=False)

s1 = ui.switch('Toggle dark mode', on_change=toggle_dark)

ui.add_head_html("""
<style>
.body--dark .card-changed {
    background-color: #6B3400;
}

.body--light .card-changed {
    background-color: #FFEECC;
}
</style>
""")

def to_base64(path, picname):
    fullpath = os.path.join(path, picname)

    with open(fullpath, 'rb') as f:
        return 'data:image/png;base64, '+str(base64.b64encode(f.read()),encoding='utf-8')

def endswithmany(str, list_of_extensions):
    return np.any([str.endswith(i) for i in list_of_extensions])

def filename(str):
    filenameparts = str.split('.')
    return {'filename':'.'.join(filenameparts[:-1]),
            'extension': filenameparts[-1],
            'fullname': str}

class Dataset:
    def __init__(self) -> None:
        self.path = None
        self.is_ready = False
        self.unsaved_changes = 0
        self.cards = []
        self.save_option = ".txt"
        pass

    def read_path(self, path):
        self.path = path
        self.is_ready = True

        self.unsaved_changes = 0
        self.cards = []

        files = sorted(os.listdir(path))

        pictures = [filename(i) for i in files if endswithmany(i.lower(), ['.jpg','.png','.jpeg'])]
        texts = [filename(i) for i in files if endswithmany(i.lower(), ['.txt','.caption'])]

        if len(texts) > 0:
            output_texts = []
            if len(texts) != len(pictures):
                with ui.card().classes('bg-warning') as card:
                    ui.label(f'In dataset found {len(pictures)} image files, but {len(texts)} text files.')

            #attempt to associate text file with picture
            for picture in pictures:
                corresponding_text = [i for i in texts if i['filename']==picture['filename']]
                if len(corresponding_text) == 0:
                    output_texts.append('')
                elif len(corresponding_text) > 1:
                    with ui.card().classes('bg-warning') as card:
                        bad_files = "\n\n".join([i["fullname"] for i in corresponding_text])
                        ui.markdown(f'For picture {picture["fullname"]} found too many text files:\n\n {bad_files}')
                        self.is_ready = False
                else:
                    with open(os.path.join(path, corresponding_text[0]['fullname']), 'r') as f:  # TODO proper path
                        output_texts.append(f.read())
        else:
            output_texts = ['' for _ in pictures]

        self.table = [{'fullname':pic['fullname'],
                       'txtname': pic['filename'],
                       'base64': to_base64(self.path, pic['fullname']),
                       'text': text} for pic, text in zip(pictures, output_texts)]

        self.texts = texts

    def update_text(self, i, new_text):
        if not self.is_ready:
            return

        self.table[i]['text'] = new_text
        self.unsaved_changes += 1
        #self.upd_unsaved_changes()

    def upd_unsaved_changes(self):
        if self.unsaved_changes > 0:
            ui.notify(f'{self.unsaved_changes} unsaved changes')

    def update_all_cards(self, prepend_text):
        [c.prepend_to_input(prepend_text) for c in self.cards]

    def update_selected_cards(self, append_text):
        [c.append_to_input(append_text) for c in self.cards if c.selected]

    def reset_selected_cards(self):
        [c.reset() for c in self.cards if c.selected]

    def select_deselect_all(self):
        if np.all([c.selected for c in self.cards]):
            for c in self.cards:
                c.selected = False
            ui.notify('Removed all selections')
        else:
            for c in self.cards:
                c.selected = True

    def save(self):
        for textfile in self.texts:
            os.remove(os.path.join(self.path, textfile['fullname']))

        for entry in self.table:
            with open(os.path.join(self.path, f'{entry["txtname"]}{self.save_option}'), 'w') as f:
                f.write(entry['text'])

        cards = self.cards
        [c.save() for c in cards]
        self.read_path(self.path)
        self.cards = cards


dataset = Dataset()

class DatasetCard:
    def __init__(self, element, dataset, i):
        self.i = i
        self.dataset = dataset
        self.selected = False
        self.text_in_file = element['text']

        self.card = ui.card().classes('max-w-lg')
        with self.card:
            ui.image(element["base64"])
            with ui.card_section():
                ui.checkbox(f'{element["fullname"]}').bind_value(self, 'selected')
                self.card_info = ui.markdown(f'**Previous text:**\n\n{element["text"]}')
                self.input = ui.textarea('New text',value=element["text"], on_change=lambda e: self.update_dataset(e.value))

    def update_dataset(self, text):
        self.dataset.update_text(self.i, text)
        self.card.classes('card-changed')

    def clear_card(self):
        self.card.classes(remove='card-changed')

    def prepend_to_input(self, text):
        self.input.set_value(f'{text}{self.input.value}')
        #self.update_dataset(f'{text}{self.input.value}')

    def append_to_input(self, text):
        self.input.set_value(f'{self.input.value}{text}')
        #self.update_dataset(f'{self.input.value}{text}')

    def reset(self):
        self.input.set_value(f'{self.text_in_file}')
        #self.update_dataset(f'{self.text_in_file}')
        self.clear_card()

    def save(self):
        self.card_info.set_content(f'**Previous text:**\n\n{self.input.value}')
        self.clear_card()
        self.selected = False


def fill_dataset(dataset: Dataset, path, table):
    dset_controls.clear()
    table.clear()
    dataset.read_path(path)
    if dataset.is_ready:
        with dset_controls:
            with ui.column():
                prefix = ui.input('Prefix this to all cards')
                ui.button('Prefix text to all cards', on_click=lambda: dataset.update_all_cards(prefix.value))
            with ui.column():
                suffix = ui.input('Add this to selected cards').style('min-width: 600px')
                with ui.row():
                    ui.button('Select all', on_click=lambda: dataset.select_deselect_all())
                    ui.button('Add text to the end of selected cards', on_click=lambda: dataset.update_selected_cards(suffix.value))
                    ui.button('Reset selected cards',on_click=lambda: dataset.reset_selected_cards())
            with ui.column():
                ui.label('Save captions as')
                ui.select([".txt",".caption"]).bind_value(dataset, 'save_option').style('min_width: 150px')
            ui.button('Save dataset', on_click=lambda: dataset.save()).props('color=orange').props('size=xl')
        with table:
            for i, element in enumerate(dataset.table):
                dataset.cards.append(DatasetCard(element, dataset, i))

dpath = ui.input('Dataset path',placeholder="C:\\Users\\User\\datasets\\dataset1").style('min-width: 600px')
dpath_btn = ui.button('Load dataset', on_click=lambda: fill_dataset(dataset, dpath.value, table))

#with ui.footer():  # does not work with mobile but nice idea on pc tho
dset_controls = ui.row().classes('w-full justify-between')

table = ui.row().classes('w-full')

async def scroll_top():
    await ui.run_javascript("window.scrollTo(0, 0)", respond=False)

with ui.page_sticky():
    ui.button('Scroll to the top', on_click=scroll_top)


ui.run(title='Dataset Tag Editor')