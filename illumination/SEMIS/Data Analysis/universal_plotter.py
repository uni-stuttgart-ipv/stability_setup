import plotly.graph_objects as go
from nicegui import ui
import pandas as pd
from pathlib import Path
from tkinter import Tk, filedialog

trace_list = []  # List of Trace objects

class Trace:
    def __init__(self, data, color=None, line_style='solid'):
        self.data = data
        self.source_data = data.copy()
        self.x_column_name = data.columns[0] if not data.empty else None
        self.y_column_name = data.columns[1] if not data.empty else None
        self.color = color
        self.line_style = line_style
        self.legend_name = None  # Store the legend name for this trace
        self.data_x_unit = 'base'  # Store the original x unit for this trace
        self.data_y_unit = 'base'  # Store the original y unit for this trace
        self.use_index_x = False
        self.use_index_y = False
        self.start_row = None
        self.end_row = None
        self.x_scalar = 1.0
        self.y_scalar = 1.0
        self.show_mean = False
    def change_data_units(self, x_unit, y_unit):
        self.data_x_unit = x_unit
        self.data_y_unit = y_unit
        self.data[self.x_column_name] = self.data[self.x_column_name] * UNIT_FACTORS.get(x_unit, 1.0)
        self.data[self.y_column_name] = self.data[self.y_column_name] * UNIT_FACTORS.get(y_unit, 1.0)   
# on load, give units for x and y and column names
# make function to convert time units from seconds to minutes, hours, etc. and apply to data when loading


UNIT_FACTORS = {
    'giga': 1/1e9,
    'mega': 1/1e6,
    'kilo': 0.001,
    'hecto': 0.01,
    'deca': 0.1,
    'base': 1.0,
    'deci': 10.0,
    'centi': 100.0,
    'milli': 1000.0,
    'micro': 1_000_000.0,
}


def get_trace_names():
    return [trace.legend_name for trace in trace_list if trace.legend_name]


def get_trace_by_name(trace_name):
    for trace in trace_list:
        if trace.legend_name == trace_name:
            return trace
    return None


def refresh_trace_selector(trace_selector):
    trace_names = get_trace_names()
    trace_selector.options = trace_names
    if trace_selector.value not in trace_names:
        trace_selector.value = trace_names[0] if trace_names else None
    trace_selector.update()


def open_column_mapping_dialog(data, default_trace_name, fig, plot, trace_selector, x_unit, y_unit, dialog_title='Select X and Y Columns', action_label='Add Trace', existing_trace=None):
    if data.empty:
        ui.notify('Loaded file is empty.', color='orange')
        return

    column_lookup = {str(col): col for col in data.columns}
    column_labels = list(column_lookup.keys())
    if not column_labels:
        ui.notify('No columns found in file.', color='orange')
        return

    preview_df = data.head(200).copy()
    preview_df.columns = [str(col) for col in preview_df.columns]
    preview_rows = preview_df.fillna('').astype(str).to_dict('records')
    preview_columns = [
        {'name': col, 'label': col, 'field': col, 'align': 'left'}
        for col in preview_df.columns
    ]

    default_x = column_labels[0]
    default_y = column_labels[1] if len(column_labels) > 1 else column_labels[0]
    if existing_trace is not None:
        if existing_trace.x_column_name in column_labels:
            default_x = existing_trace.x_column_name
        if existing_trace.y_column_name in column_labels:
            default_y = existing_trace.y_column_name

    with ui.dialog() as dialog, ui.card().classes('w-[1100px] max-w-[95vw]'):
        ui.label(dialog_title).classes('text-lg font-bold')
        ui.label('Preview updates live based on the settings below').classes('text-sm text-gray-600')

        with ui.row().classes('w-full gap-4 items-center'):
            x_column_select = ui.select(options=column_labels, value=default_x, label='X Column').classes('min-w-48')
            y_column_select = ui.select(options=column_labels, value=default_y, label='Y Column').classes('min-w-48')

        with ui.row().classes('w-full gap-6 items-center'):
            use_index_x = ui.switch('Use count (index) for X', value=existing_trace.use_index_x if existing_trace else False)
            use_index_y = ui.switch('Use count (index) for Y', value=existing_trace.use_index_y if existing_trace else False)

        with ui.row().classes('w-full gap-4 items-center'):
            start_row_input = ui.input(label='Start Row (optional)', value='' if not existing_trace or existing_trace.start_row is None else str(existing_trace.start_row)).props('type=number').classes('min-w-40')
            end_row_input = ui.input(label='End Row (optional)', value='' if not existing_trace or existing_trace.end_row is None else str(existing_trace.end_row)).props('type=number').classes('min-w-40')
            x_scale_input = ui.input(label='X Scalar', value=str(existing_trace.x_scalar) if existing_trace else '1.0').classes('min-w-32')
            y_scale_input = ui.input(label='Y Scalar', value=str(existing_trace.y_scalar) if existing_trace else '1.0').classes('min-w-32')

        with ui.row().classes('w-full gap-4 items-center'):
            color_input = ui.input(label='Trace Color (Hex)', value=existing_trace.color if existing_trace and existing_trace.color else '', placeholder='#1f77b4').classes('min-w-48')
            line_style_selector = ui.select(
                options=['solid', 'dash', 'dot', 'dashdot'],
                value=existing_trace.line_style if existing_trace else 'solid',
                label='Line Style',
            ).classes('min-w-32')

        trace_name_input = ui.input(label='Trace Name', value=default_trace_name).classes('w-full')
        preview_status = ui.label('').classes('text-sm text-gray-600')
        preview_table = ui.table(columns=preview_columns, rows=preview_rows).classes('w-full h-64')

        def _parse_scalar(text_value, axis_name):
            text = (text_value or '').strip()
            if text == '':
                return 1.0, None
            try:
                return float(text), None
            except ValueError:
                return None, f'Invalid {axis_name} scalar: {text}'

        def _parse_row_bounds(total_rows):
            start_text = (start_row_input.value or '').strip()
            end_text = (end_row_input.value or '').strip()

            try:
                start_row = int(start_text) if start_text else 0
                end_row = int(end_text) if end_text else total_rows - 1
            except ValueError:
                return None, None, 'Start/End row must be integers'

            if total_rows == 0:
                return 0, -1, None

            start_row = max(0, min(start_row, total_rows - 1))
            end_row = max(0, min(end_row, total_rows - 1))

            if end_row < start_row:
                return None, None, 'End row must be greater than or equal to start row'

            return start_row, end_row, None

        def _build_processed_data():
            start_row, end_row, row_error = _parse_row_bounds(len(data))
            if row_error:
                return None, row_error

            subset = data.iloc[start_row:end_row + 1].copy()
            if subset.empty:
                return pd.DataFrame(columns=['row_index', 'x', 'y']), None

            x_scalar, x_scalar_error = _parse_scalar(x_scale_input.value, 'X')
            if x_scalar_error:
                return None, x_scalar_error

            y_scalar, y_scalar_error = _parse_scalar(y_scale_input.value, 'Y')
            if y_scalar_error:
                return None, y_scalar_error

            if use_index_x.value:
                x_series = pd.Series(range(len(subset)), index=subset.index)
            else:
                x_col = column_lookup[x_column_select.value]
                x_series = pd.to_numeric(subset[x_col], errors='coerce')

            if use_index_y.value:
                y_series = pd.Series(range(len(subset)), index=subset.index)
            else:
                y_col = column_lookup[y_column_select.value]
                y_series = pd.to_numeric(subset[y_col], errors='coerce')

            processed = pd.DataFrame(
                {
                    'row_index': subset.index,
                    'x': x_series * x_scalar,
                    'y': y_series * y_scalar,
                },
                index=subset.index,
            ).dropna(subset=['x', 'y'])
            return processed, None

        def _refresh_preview():
            processed, error_message = _build_processed_data()
            if error_message:
                preview_status.text = error_message
                preview_status.update()
                preview_table.rows = []
                preview_table.update()
                return

            preview = processed.head(200).copy()
            preview_rows_local = preview.fillna('').astype(str).to_dict('records')
            preview_table.columns = [
                {'name': 'row_index', 'label': 'row_index', 'field': 'row_index', 'align': 'left'},
                {'name': 'x', 'label': 'x', 'field': 'x', 'align': 'left'},
                {'name': 'y', 'label': 'y', 'field': 'y', 'align': 'left'},
            ]
            preview_table.rows = preview_rows_local
            preview_table.update()
            preview_status.text = f'{len(processed)} valid rows (showing up to 200)'
            preview_status.update()

        x_column_select.on_value_change(lambda _: _refresh_preview())
        y_column_select.on_value_change(lambda _: _refresh_preview())
        use_index_x.on_value_change(lambda _: _refresh_preview())
        use_index_y.on_value_change(lambda _: _refresh_preview())
        start_row_input.on_value_change(lambda _: _refresh_preview())
        end_row_input.on_value_change(lambda _: _refresh_preview())
        x_scale_input.on_value_change(lambda _: _refresh_preview())
        y_scale_input.on_value_change(lambda _: _refresh_preview())

        _refresh_preview()

        def add_trace_from_selection():
            final_trace_name = (trace_name_input.value or '').strip() or default_trace_name
            cleaned_color = (color_input.value or '').strip()
            if cleaned_color and (not cleaned_color.startswith('#') or len(cleaned_color) != 7):
                ui.notify('Use hex color format like #1f77b4', color='orange')
                return

            plot_data, error_message = _build_processed_data()
            if error_message:
                ui.notify(error_message, color='orange')
                return
            if plot_data.empty:
                ui.notify('Selected X/Y data has no valid numeric rows.', color='orange')
                return

            conflicting_trace = get_trace_by_name(final_trace_name)
            if conflicting_trace is not None and conflicting_trace is not existing_trace:
                trace_list.remove(conflicting_trace)

            target_trace = existing_trace
            if target_trace is None:
                target_trace = Trace(data=plot_data, color=cleaned_color or None, line_style=line_style_selector.value or 'solid')
                trace_list.append(target_trace)

            target_trace.data = plot_data
            target_trace.source_data = data.copy()
            target_trace.color = cleaned_color or None
            target_trace.line_style = line_style_selector.value or 'solid'
            target_trace.legend_name = final_trace_name
            target_trace.x_column_name = 'x'
            target_trace.y_column_name = 'y'
            target_trace.use_index_x = bool(use_index_x.value)
            target_trace.use_index_y = bool(use_index_y.value)
            target_trace.start_row = int(start_row_input.value) if (start_row_input.value or '').strip() else None
            target_trace.end_row = int(end_row_input.value) if (end_row_input.value or '').strip() else None
            target_trace.x_scalar = float(x_scale_input.value or 1.0)
            target_trace.y_scalar = float(y_scale_input.value or 1.0)

            refresh_trace_selector(trace_selector)
            redraw_all_traces(fig, plot, x_unit, y_unit)
            ui.notify(f'Saved trace: {final_trace_name}', color='green')
            dialog.close()

        with ui.row().classes('w-full justify-end gap-2'):
            ui.button('Cancel', on_click=dialog.close).props('flat')
            ui.button(action_label, on_click=add_trace_from_selection).classes('bg-blue-500 text-white')

    dialog.open()


def get_trace_stats(trace_obj, x_unit='base', y_unit='base'):
    if trace_obj is None or trace_obj.data.empty:
        return {'count': 0, 'mean_y': None, 'std_y': None}

    y_factor = UNIT_FACTORS.get(y_unit, 1.0)
    y_values = pd.to_numeric(trace_obj.data[trace_obj.y_column_name], errors='coerce') * y_factor
    y_values = y_values.dropna()
    if y_values.empty:
        return {'count': 0, 'mean_y': None, 'std_y': None}

    return {
        'count': int(len(y_values)),
        'mean_y': float(y_values.mean()),
        'std_y': float(y_values.std()),
    }


def update_trace_info_label(info_label, trace_name, y_unit='base'):
    trace_obj = get_trace_by_name(trace_name)
    if trace_obj is None:
        info_label.text = 'No trace selected'
        info_label.update()
        return

    stats = get_trace_stats(trace_obj, y_unit=y_unit)
    mean_text = 'n/a' if stats['mean_y'] is None else f"{stats['mean_y']:.6g}"
    std_text = 'n/a' if stats['std_y'] is None else f"{stats['std_y']:.6g}"
    info_label.text = f"Points: {stats['count']} | Mean(Y): {mean_text} | Std(Y): {std_text}"
    info_label.update()


def open_trace_info_dialog(trace_name, y_unit='base'):
    trace_obj = get_trace_by_name(trace_name)
    if trace_obj is None:
        ui.notify('Select a valid trace first', color='orange')
        return

    stats = get_trace_stats(trace_obj, y_unit=y_unit)
    mean_text = 'n/a' if stats['mean_y'] is None else f"{stats['mean_y']:.6g}"
    std_text = 'n/a' if stats['std_y'] is None else f"{stats['std_y']:.6g}"

    with ui.dialog() as dialog, ui.card().classes('w-[700px] max-w-[95vw]'):
        ui.label(f'Trace Information: {trace_obj.legend_name}').classes('text-lg font-bold')
        ui.label(f'Points: {stats["count"]}')
        ui.label(f'Mean(Y): {mean_text}')
        ui.label(f'Std(Y): {std_text}')
        ui.separator()
        ui.label(f'Line style: {trace_obj.line_style or "solid"}')
        ui.label(f'Color: {trace_obj.color or "default"}')
        ui.label(f'Use index X: {trace_obj.use_index_x}')
        ui.label(f'Use index Y: {trace_obj.use_index_y}')
        ui.label(f'Start row: {trace_obj.start_row if trace_obj.start_row is not None else "start"}')
        ui.label(f'End row: {trace_obj.end_row if trace_obj.end_row is not None else "end"}')
        ui.label(f'X scalar: {trace_obj.x_scalar}')
        ui.label(f'Y scalar: {trace_obj.y_scalar}')
        ui.label(f'Show mean line: {trace_obj.show_mean}')
        ui.button('Close', on_click=dialog.close).classes('bg-blue-500 text-white')

    dialog.open()


def modify_trace(fig, plot, trace_name, trace_selector, x_unit, y_unit):
    trace_obj = get_trace_by_name(trace_name)
    if trace_obj is None:
        ui.notify('Select a valid trace first', color='orange')
        return

    source_data = trace_obj.source_data.copy() if trace_obj.source_data is not None else trace_obj.data.copy()
    open_column_mapping_dialog(
        source_data,
        trace_obj.legend_name,
        fig,
        plot,
        trace_selector,
        x_unit,
        y_unit,
        dialog_title='Modify Trace',
        action_label='Save Changes',
        existing_trace=trace_obj,
    )


def set_trace_mean_line(fig, plot, trace_name, enabled, x_unit, y_unit):
    trace_obj = get_trace_by_name(trace_name)
    if trace_obj is None:
        ui.notify('Select a valid trace first', color='orange')
        return

    trace_obj.show_mean = bool(enabled)
    redraw_all_traces(fig, plot, x_unit, y_unit)
    ui.notify(f'Mean line {"enabled" if enabled else "disabled"} for {trace_name}', color='green')


def redraw_all_traces(fig, plot, x_unit='base', y_unit='base'):
    x_factor = UNIT_FACTORS.get(x_unit, 1.0)
    y_factor = UNIT_FACTORS.get(y_unit, 1.0)

    fig.data = []
    for trace_obj in trace_list:
        if not trace_obj.legend_name:
            continue
        trace_name = trace_obj.legend_name
        data = trace_obj.data
        line_style = trace_obj.line_style or 'solid'
        line_color = trace_obj.color

        line_dict = {'dash': line_style}
        if line_color:
            line_dict['color'] = line_color

        fig.add_trace(
            go.Scatter(
                x=data[trace_obj.x_column_name] * x_factor,
                y=data[trace_obj.y_column_name] * y_factor,
                mode='lines',
                name=trace_name,
                line=line_dict,
            )
        )

        if trace_obj.show_mean:
            x_values = pd.to_numeric(data[trace_obj.x_column_name], errors='coerce') * x_factor
            y_values = pd.to_numeric(data[trace_obj.y_column_name], errors='coerce') * y_factor
            x_values = x_values.dropna()
            y_values = y_values.dropna()
            if not x_values.empty and not y_values.empty:
                mean_y = float(y_values.mean())
                fig.add_trace(
                    go.Scatter(
                        x=[x_values.min(), x_values.max()],
                        y=[mean_y, mean_y],
                        mode='lines',
                        name=f'{trace_name} mean = {mean_y:.6g}',
                        line={'dash': 'dot', 'color': line_color or '#666666'},
                        showlegend=True,
                    )
                )

    fig.update_layout(
        xaxis_title=f'{x_label.value or "a.u."}',
        yaxis_title=f'{y_label.value or "a.u."}',
    )
    update_plot(plot)


def apply_trace_style(fig, plot, trace_name, color_hex, line_style, x_unit, y_unit):
    trace_obj = get_trace_by_name(trace_name)
    if trace_obj is None:
        ui.notify('Select a valid trace first', color='orange')
        return

    cleaned_color = (color_hex or '').strip()
    if cleaned_color and (not cleaned_color.startswith('#') or len(cleaned_color) != 7):
        ui.notify('Use hex color format like #1f77b4', color='orange')
        return

    trace_obj.color = cleaned_color or None
    trace_obj.line_style = line_style or 'solid'

    redraw_all_traces(fig, plot, x_unit, y_unit)
    ui.notify(f'Updated style for {trace_name}', color='green')


def apply_axis_units(fig, plot, x_unit, y_unit):
    redraw_all_traces(fig, plot, x_unit, y_unit)
    ui.notify(f'Applied axis units: X={x_unit}, Y={y_unit}', color='green')

def get_solar_AM15D():
    # Standard solar spectrum data
    AM1_5G_path = r"C:\Users\aleja\Documents\iPV\00-SEMIS_repo\SEMIS\Data Analysis\astmg173.xls"
    df_AM1_5G = pd.read_excel(AM1_5G_path, skiprows=1, names=["wavelength [nm]", "Etr [W/m2]", "global tilt [W/m2]", "direct+circumsolar [W/m2]"], sheet_name=0)

    # Group by every 2 rows and sum, keeping the first wavelength value
    Solar_spectrum_binned = pd.DataFrame()
    Solar_spectrum_binned = df_AM1_5G.iloc[::1].reset_index(drop=True).copy()
    Solar_spectrum_binned['Etr [W/m2]'] += df_AM1_5G.iloc[0::1]['Etr [W/m2]'].values
    Solar_spectrum_binned['global tilt [W/m2]'] += df_AM1_5G.iloc[0::1]['global tilt [W/m2]'].values
    Solar_spectrum_binned['direct+circumsolar [W/m2]'] += df_AM1_5G.iloc[0::1]['direct+circumsolar [W/m2]'].values

    for col in ['Etr [W/m2]', 'global tilt [W/m2]', 'direct+circumsolar [W/m2]']:
        Solar_spectrum_binned[col] = Solar_spectrum_binned[col]/2

    return Solar_spectrum_binned

def format_plotly_for_latex(fig):
    fig.update_layout(
        font=dict(family="Times New Roman", size=16, color="black"),
        
        plot_bgcolor='white',
        paper_bgcolor='white',
        # width=800,
        # height=400,
        title_font=dict(size=14, family="Times New Roman"),
        legend_font=dict(size=10, family="Times New Roman"),
        margin=dict(l=90, r=50, t=40, b=80),
    )
    return fig

def show_legend(fig, show):
    fig.update_layout(showlegend=show)
    return fig

def format_legend(fig, x=0.98, y=0.95, xanchor='right', yanchor='top'):
    legend=dict(
        x=x,
        y=y,
        xanchor=xanchor,
        yanchor=yanchor,
        bgcolor='rgba(255,255,255,0.9)',
        bordercolor='black',
        
        borderwidth=1,
        font=dict(family='Times New Roman', size=13, color='black')
    )
    fig.update_layout(legend=legend)
    return fig

def update_plot(plot):
    plot.update()

def clear_plot(plot, trace_selector):
    plot.figure.data = []
    update_plot(plot)
    trace_list.clear()  # Clear the stored traces as well
    refresh_trace_selector(trace_selector)
    ui.notify('Plot cleared', color='green')

def load_data(fig, plot, trace_name, trace_selector, x_unit, y_unit):
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    selected_path = filedialog.askopenfilename(
        title='Select data file',
        filetypes=[
            ('Data files', '*.csv *.txt *.xlsx *.xls'),
            ('CSV files', '*.csv'),
            ('Excel files', '*.xlsx *.xls'),
            ('Text files', '*.txt'),
            ('All files', '*.*'),
        ],
    )
    root.destroy()

    if not selected_path:
        ui.notify('No file selected')
        return

    try:
        extension = Path(selected_path).suffix.lower()
        if extension in ['.csv', '.txt']:
            data = pd.read_csv(selected_path, sep=None, engine='python')
        elif extension in ['.xlsx', '.xls']:
            data = pd.read_excel(selected_path)
        else:
            ui.notify('Unsupported file type')
            return
        ui.notify(f'Loaded data from {Path(selected_path).name}')
    except Exception as e:
        ui.notify(f'Error loading file: {e}')
        return

    default_trace_name = (trace_name or '').strip() or Path(selected_path).stem
    open_column_mapping_dialog(
        data,
        default_trace_name,
        fig,
        plot,
        trace_selector,
        x_unit,
        y_unit,
        dialog_title='Load Trace',
        action_label='Add Trace',
        existing_trace=None,
    )

def remove_trace(trace_name, trace_selector, x_unit, y_unit):
    trace_obj = get_trace_by_name(trace_name)
    if trace_obj is not None:
        trace_list.remove(trace_obj)
        refresh_trace_selector(trace_selector)
        redraw_all_traces(fig, plot, x_unit, y_unit)
        ui.notify(f'Removed trace: {trace_name}', color='red')
    else:
        ui.notify(f'Trace not found: {trace_name}', color='orange')

# Create main container with flexbox layout
with ui.row().classes('w-full h-screen gap-4 p-4 flex-nowrap items-stretch box-border'):
    # LEFT PANEL - Controls
    with ui.column().classes('w-80 shrink-0 gap-4 border rounded p-4 box-border'):
        ui.label('Plot Parameters').classes('text-lg font-bold')
        
        with ui.row().classes('gap-2'):
            trace_name = ui.input(label='Trace Name')
            ui.button('Load Data', on_click=lambda: load_data(fig, plot, trace_name.value, trace_selector, x_unit_selector.value, y_unit_selector.value)).classes('bg-blue-500 text-white')
        x_label = ui.input(label='X Label')
        y_label = ui.input(label='Y Label')

        with ui.row().classes('gap-2 items-center'):
            x_unit_selector = ui.select(options=list(UNIT_FACTORS.keys()), value='base', label='X Unit Scale').classes('min-w-32')
            y_unit_selector = ui.select(options=list(UNIT_FACTORS.keys()), value='base', label='Y Unit Scale').classes('min-w-32')
            ui.button('Apply Units', on_click=lambda: apply_axis_units(fig, plot, x_unit_selector.value, y_unit_selector.value)).classes('bg-indigo-500 text-white')

        ui.switch('Show Legend', on_change=lambda e: show_legend(fig, e.value)).classes('mb-2')

        # Dummy buttons
        with ui.row().classes('gap-2'):
            ui.button('Clear Plot', on_click=lambda: clear_plot(plot, trace_selector)).classes('bg-red-500 text-white')
            
            ui.button('Update plot', on_click=lambda: update_plot(plot)).classes('bg-green-500 text-white')
        
        ui.label('Trace Parameters').classes('text-lg font-bold')
        with ui.row().classes('gap-2'):
            trace_selector = ui.select(options=[], label='Traces').classes('min-w-48')
            ui.button('Remove trace', on_click=lambda: remove_trace(trace_selector.value, trace_selector, x_unit_selector.value, y_unit_selector.value)).classes('bg-yellow-500 text-white')

        with ui.row().classes('gap-2 items-center'):
            color_input = ui.input(label='Line Color (Hex)', placeholder='#1f77b4').classes('min-w-30')
            line_style_selector = ui.select(
                options=['solid', 'dash', 'dot', 'dashdot'],
                value='solid',
                label='Line Style',
            ).classes('min-w-32')

        with ui.row().classes('gap-2 items-center'):
            show_mean_switch = ui.switch('Show Mean Line', value=False)
            ui.button(
                'Apply Mean Option',
                on_click=lambda: set_trace_mean_line(
                    fig,
                    plot,
                    trace_selector.value,
                    show_mean_switch.value,
                    x_unit_selector.value,
                    y_unit_selector.value,
                ),
            ).classes('bg-cyan-600 text-white')

        trace_info_label = ui.label('No trace selected').classes('text-sm text-gray-700')

        def _sync_trace_controls(selected_name):
            trace_obj = get_trace_by_name(selected_name)
            show_mean_switch.value = bool(trace_obj.show_mean) if trace_obj else False
            show_mean_switch.update()
            update_trace_info_label(trace_info_label, selected_name, y_unit_selector.value)

        trace_selector.on_value_change(lambda e: _sync_trace_controls(e.value))

        with ui.row().classes('gap-2'):
            ui.button('Show Trace Info', on_click=lambda: open_trace_info_dialog(trace_selector.value, y_unit_selector.value)).classes('bg-slate-600 text-white')
            ui.button(
                'Modify Trace',
                on_click=lambda: modify_trace(
                    fig,
                    plot,
                    trace_selector.value,
                    trace_selector,
                    x_unit_selector.value,
                    y_unit_selector.value,
                ),
            ).classes('bg-orange-600 text-white')

        ui.button(
            'Apply Trace Style',
            on_click=lambda: apply_trace_style(
                fig,
                plot,
                trace_selector.value,
                color_input.value,
                line_style_selector.value,
                x_unit_selector.value,
                y_unit_selector.value,
            ),
        ).classes('bg-purple-600 text-white')
        
    # RIGHT PANEL - Plots
    with ui.column().classes('flex-1 min-w-0 gap-4 border rounded p-4 box-border'):
        ui.label('Plot Area').classes('text-lg font-bold')
        
        # Create a sample plot
        fig = go.Figure()
        # x_data = np.linspace(0, 10, 100)
        # y_data = np.sin(x_data)
        # fig.add_trace(go.Scatter(x=x_data, y=y_data, mode='lines', name='Sample Data'))
        fig = format_plotly_for_latex(fig)
        fig = format_legend(fig)
        fig = show_legend(fig, True)
        plot = ui.plotly(fig).classes('w-full flex-1')
    

# BOTTOM PANEL - Action Buttons
with ui.row().classes('w-full gap-4 p-4 border rounded box-border'):
    # ui.button('Run Analysis', on_click=lambda: ui.notify('Analysis started'))
    # ui.button('Save Results', on_click=lambda: ui.notify('Results saved'))
    # ui.button('Reset', on_click=lambda: ui.notify('Reset clicked'))
    # ui.space()
    ui.button('Exit', on_click=lambda: None)

ui.run(fullscreen=False, title='Universal Plotter')