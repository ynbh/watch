from homepage import get_relevant_results
from constants import HOME


from textual.app import App
from textual.widgets import DataTable

class SelectMedia(App):
    
    CSS = "DataTable { height: 100%; width: 100%; }" 
    
    def __init__(self, data):
        super().__init__()
        self.data = data 
    
    def compose(self):
        dt = DataTable(zebra_stripes=True)
        columns = self.data[0].keys()
        for column in columns:
            if column != "poster":
                dt.add_column(column.capitalize())
        
        for item in self.data:
            row = []
            for key in columns:
                if key != "poster":
                    if key == "url":
                        row.append(f"{HOME}{item[key]}" if item[key] else "N/A")
                    else:
                        row.append(str(item[key]) if item[key] is not None else "N/A")
            dt.add_row(*row)
        dt.cursor_type = "row"
        dt.focus()
        yield dt 
    
    def on_data_table_row_selected(self, event):
        row_key = event.row_key 
        row = event.control.get_row(row_key)
        self.notify(f"Selected: {row}") 

if __name__ == "__main__":
    term = input("Enter search term: ")
    results = get_relevant_results(term)
    media = SelectMedia(data=results)
    media.run()
