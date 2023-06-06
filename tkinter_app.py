import itk
import itkwidgets
import tkinter as tk
from tkinter import filedialog, Tk, Canvas, Entry, Text, Button, PhotoImage, Radiobutton,StringVar, W
from PIL import ImageTk, Image
import subprocess
import pyvista
import SimpleITK as sitk
import sys
import time
import numpy as np
from tqdm import tqdm
import cv2
import os
from pathlib import Path
import threading


pyvista.global_theme.transparent_background = True
sys.path.insert(1, 'simpleITK-Snap')
import SimpleITKSnap as sis

def sitk_snap_ext(image):
    from SimpleITKSnap.Extension import histogram
    np_image = sitk.GetArrayFromImage(image)
    sis.imshow(np_image, histogram)


def read_bmp_directory_itkimage(bmp_directory, resize_shape = None, start = 500, finish = 3500,resize = False, threshold = False):
    if bmp_directory == '':
        return None
    images = [f for f in sorted(os.listdir(bmp_directory), key=lambda x: int(x.split('_')[1].split('.')[0])) if f.endswith("bmp")]
    volume_np = []
    print(len(images))
    for image in tqdm(images[start:finish]):
        im = itk.GetArrayFromImage(itk.imread(os.path.join(bmp_directory, image), itk.UC))
        if resize :
            im = cv2.resize(im, [resize_shape, resize_shape])
        if threshold :
            _,im = cv2.threshold(im, 74, 255, cv2.THRESH_BINARY)
        volume_np.append(im)
    
    volume_np = np.array(volume_np)
    print(volume_np.shape)
    volume = sitk.GetImageFromArray(volume_np)
    volume.SetSpacing([0.005, 0.005, 0.005])
    
    
    return volume    

class ITKVolumeApp:
    def __init__(self, root):
        self.root = root
        self.volume = None
        self.update_slice_0 = 0
        self.sep  = 0   
        self.load = 0
        self.slider = 0
        self.viewer = None
        self.image_tk = None
        self.create_widgets()

    def _create_circle(self, x, y, r, **kwargs):
        return self.canvas.create_oval(x-r, y-r, x+r, y+r, **kwargs)

    def sitk2itk(self,image_sitk):
        volume = itk.GetImageFromArray(sitk.GetArrayFromImage(image_sitk))
        volume.SetSpacing(image_sitk.GetSpacing())
        volume.SetOrigin(image_sitk.GetOrigin())

        return volume
    
    def itk2sitk(self, image_itk):
        volume = sitk.GetImageFromArray(itk.GetArrayFromImage(image_itk))
        return volume
    def sitk2pyvista(self, image_sitk):
        writer = sitk.ImageFileWriter()
        writer.SetFileName(os.path.dirname(self.file_path)+ "/pyvista_volume.nii.gz")
        writer.Execute(image_sitk)  
        return pyvista.get_reader(os.path.dirname(self.file_path)+ "/pyvista_volume.nii.gz")
          

    def load_volume_dicom(self):
        self.canvas.create_circle(x = 10, y = 10, r = 10, fill="red", outline="#DDD", width=4)
        print("Loading volume Dicom")
        if self.slider != 0 : 
            self.slider_min.destroy()
            self.slider_max.destroy()
        self.file_path = filedialog.askdirectory()
        self.sitk_image = read_bmp_directory_itkimage(self.file_path, resize_shape = None, start = 0, finish = None)

        self.volume = self.sitk_image

        self.volume_pv = self.sitk2pyvista(self.sitk_image)
        print("Volume loaded successfully.")
        loaded = tk.Label(self.root, text = "Volume loaded successfully !")
        loaded.place(x=50, y = 50)
        loaded.pack()
        loaded.destroy()

        if len(np.unique(sitk.GetArrayFromImage(self.volume)[0])) > 3:
            print("NOT SEGMENTED PROPERLY")
            loaded = tk.Label(self.root, text = " Can't separate :  Not segmented")
            loaded.place(x=20, y = 10)

        self.scale_min_var = tk.DoubleVar()
        self.scale_min_var.set(1)
        self.scale_max_var = tk.DoubleVar()
        self.scale_max_var.set(1)
        self.slider_min = tk.Scale(
                self.root,
                from_=0,
                to=len(sitk.GetArrayFromImage(self.volume)),
                orient='horizontal',  # horizontal
                variable = self.scale_min_var
            )
        self.slider_min.place(x=455.0,
            y=52.0)
        self.slider_max = tk.Scale(
                self.root,
                from_=self.slider_min.get(),
                to=len(sitk.GetArrayFromImage(self.volume)),
                orient='horizontal',  # horizontal
                variable = self.scale_max_var)            
        self.slider_max.place(            
            x=455.0,
            y=122.0,)
        self.slider_min.pack()
        self.slider_max.pack()
        self.canvas.create_circle(x = 10, y = 10, r = 10, fill="green", outline="#DDD", width=4)

    def extract_intensity(self,images, intensity):
        # Create a new image with the same shape as the original image
        
        extracted_volume = []
        for image in images : 
            extracted_image = np.zeros_like(image)

            # Set pixels with the specified intensity to the original intensity value
            extracted_image[image == intensity] = intensity
            
            extracted_volume.append(extracted_image)
        
        extracted_volume = np.array(extracted_volume)
        print(extracted_volume.shape)

        return sitk.GetImageFromArray(extracted_volume)

    def load_volume_dicom_in_background(self):
        thread = threading.Thread(target=self.load_volume_dicom)
        thread.start()
    def load_volume(self):
        self.canvas.create_circle(x = 10, y = 10, r = 10, fill="red", outline="#DDD", width=4)

        # Open a file dialog to select the NRRD volume
        print("Loading volume")

        self.file_path = filedialog.askopenfilename(title = "Select volume",filetypes=[("NRRD Files", "*.nrrd"),("Niifti FFiles .nii.gz","*.nii.gz"),("Niifti Files .nii", "*.nii")])
        if self.file_path:
            # Load the NRRD volume
            self.volume = itk.imread(self.file_path)
            self.volume = self.itk2sitk(self.volume)

            if self.file_path.endswith("nii.gz") or self.file_path.endswith(".nii"):
                print("Nifti File")
                class NIFTIReader(pyvista.BaseReader):
                    import vtk
                    _class_reader = vtk.vtkNIFTIImageReader
                reader = NIFTIReader(self.file_path)
                self.volume_pv = reader
            else : 
                self.volume_pv = pyvista.get_reader(self.file_path)
            print("Volume loaded successfully.")


            if len(np.unique(sitk.GetArrayFromImage(self.volume)[0])) > 3:
                print("NOT SEGMENTED PROPERLY")
                loaded = tk.Label(self.root, text = " Can't separate :  Not segmented")
                loaded.place(x=20, y = 10)

            self.scale_min_var = tk.DoubleVar()
            self.scale_min_var.set(1)
            self.scale_max_var = tk.DoubleVar()
            self.scale_max_var.set(1)


            self.slider_min = tk.Scale(
                self.root,
                from_=0,
                to=len(sitk.GetArrayFromImage(self.volume)),
                orient='horizontal',  # horizontal
                variable = self.scale_min_var
            )
            self.slider_max = tk.Scale(
                self.root,
                from_=self.slider_min.get(),
                to=len(sitk.GetArrayFromImage(self.volume)),
                orient='horizontal',  # horizontal
                variable = self.scale_max_var)  
            if self.load !=0: # already loaded
                self.load = 1
                self.slider_max.destroy()
                self.slider_min.destroy()
            self.slider_min.place(x=455.0,
            y=52.0)         
            self.slider_max.place(            
            x=300.0,
            y=122.0,)
            self.slider_min.pack()
            self.slider_max.pack()

        self.canvas.create_circle(x = 10, y = 10, r = 10, fill="green", outline="#DDD", width=4)

    def load_volume_in_background(self):
        thread = threading.Thread(target=self.load_volume)
        thread.start()
    def slice_volume(self):
        self.canvas.create_circle(x = 10, y = 10, r = 10, fill="red", outline="#DDD", width=4)

        print("min",self.scale_min_var.get(),"max",self.scale_max_var.get())
        self.volume_sliced = sitk.GetImageFromArray(sitk.GetArrayFromImage(self.volume)[int(self.scale_min_var.get()) : int(self.scale_max_var.get())])
        writer = sitk.ImageFileWriter()
        self.output_path_slice =os.path.dirname(self.file_path)+ "/volume_sliced.nii.gz"
        print("Output:",self.output_path_slice)
        writer.SetFileName(self.output_path_slice)
        writer.Execute(self.volume_sliced)
        self.volume = self.volume_sliced

        self.canvas.create_circle(x = 10, y = 10, r = 10, fill="green", outline="#DDD", width=4)

    def slice_volume_in_background(self):
        thread = threading.Thread(target=self.slice_volume)
        thread.start()
    def show_viewer(self):
        self.canvas.create_circle(x = 10, y = 10, r = 10, fill="red", outline="#DDD", width=4)

        if self.volume is not None:
            print("Slicing : choose boundaries")

            self.volume = itk.imread(self.output_path_slice)
            self.volume = self.itk2sitk(self.volume)
            if self.file_path.endswith("nii.gz") or self.file_path.endswith(".nii"):
                print("Nifti File")
                class NIFTIReader(pyvista.BaseReader):
                    import vtk
                    _class_reader = vtk.vtkNIFTIImageReader
                reader = NIFTIReader(self.output_path_slice)
                self.volume_pv = reader
            else : 
                self.volume_pv = pyvista.get_reader(self.output_path_slice)
            print("Rendering..")

            mesh = self.volume_pv.read()
            # Plot the PyVista grid
            # mesh.plot(volume = True,cmap = 'bone', opacity = 'sigmoid',
            #           show_axes = True, text = "Volume Rendering", )
            p = pyvista.Plotter()
            p.add_volume_clip_plane(mesh, cmap = "bone", opacity = "sigmoid",normal ='z', tubing = True)
            p.show()
        else:
            print("No volume loaded.")
        self.canvas.create_circle(x = 10, y = 10, r = 10, fill="green", outline="#DDD", width=4)
    def show_viewer_in_background(self):
        thread = threading.Thread(target=self.show_viewer)
        thread.start()
    def view_snap(self):
        self.canvas.create_circle(x = 10, y = 10, r = 10, fill="red", outline="#DDD", width=4)
        print("Snapping")
        if self.volume is not None:
            sitk_snap_ext(self.volume)
        self.canvas.create_circle(x = 10, y = 10, r = 10, fill="green", outline="#DDD", width=4)
    def view_snap_in_background(self):
        thread = threading.Thread(target=self.view_snap)
        thread.start()
    def show_cortical(self):
        self.canvas.create_circle(x = 10, y = 10, r = 10, fill="red", outline="#DDD", width=4)
        print("Showing cortical")
        print(np.unique(sitk.GetArrayFromImage(self.cortical_compartiment_mask)))
        pv_cortical = self.sitk2pyvista(self.cortical_compartiment_mask)
        mesh_cortical = pv_cortical.read()
        p = pyvista.Plotter()
        p.add_volume_clip_plane(mesh_cortical, cmap = "bone", opacity = "sigmoid", normal ='z', tubing = True)
        p.show()   
        sitk_snap_ext(self.cortical_compartiment_mask)
        self.canvas.create_circle(x = 10, y = 10, r = 10, fill="green", outline="#DDD", width=4)
    def show_cortical_in_background(self):
        thread = threading.Thread(target=self.show_cortical)
        thread.start()

    def show_trabecular(self):
        self.canvas.create_circle(x = 10, y = 10, r = 10, fill="red", outline="#DDD", width=4)
        print("Showing trabecular")
        print(np.unique(sitk.GetArrayFromImage(self.trabecular_compartiment_mask)))
        pv_trabecular = self.sitk2pyvista(self.trabecular_compartiment_mask)
        mesh_trabecular = pv_trabecular.read()
        p = pyvista.Plotter()
        p.add_volume_clip_plane(mesh_trabecular, cmap = "bone", opacity = "sigmoid", normal ='z')
        p.show()
        sitk_snap_ext(self.trabecular_compartiment_mask)
        self.canvas.create_circle(x = 10, y = 10, r = 10, fill="green", outline="#DDD", width=4)

    def show_trabecular_in_background(self):
        thread = threading.Thread(target=self.show_trabecular)
        thread.start()
    def separate_bones(self):

        print("Separating")
        self.canvas.create_circle(x = 10, y = 10, r = 10, fill="red", outline="#DDD", width=4)

        self.cortical_compartiment_mask = sitk.RescaleIntensity(self.extract_intensity(sitk.GetArrayFromImage(self.volume_sliced), intensity = 85), 0,255)
        self.trabecular_compartiment_mask = sitk.RescaleIntensity(self.extract_intensity(sitk.GetArrayFromImage(self.volume_sliced), intensity = 171),0,255)
        loaded = tk.Label(self.root, text = "Bones separated successfully !")
        loaded.place(x=250, y = 150)
        loaded.pack()
        loaded.destroy()

        r1 = Button(self.root, text="Cortical mask", command = self.show_cortical_in_background)

        r2 = Button(self.root, text="Trabecular mask", command = self.show_trabecular_in_background)
        if self.sep !=0:
            r1.destroy()
            r2.destroy()
        r1.place(
            x=450.0,
            y=402.0,
        )

        r2.place(
            x=450.0,
            y=440.0,

        )
        self.sep = 1
        self.canvas.create_circle(x = 10, y = 10, r = 10, fill="green", outline="#DDD", width=4)
    
    def separate_bones_in_background(self):
        thread = threading.Thread(target=self.separate_bones)
        thread.start()

    def get_info_volume(self):
        print("Get info volume")
        #TODO
        return None

    def save_comments_written(self):
        #TODO
        print("Save written comments")
        #save comment + bone_name + path + slice number + validation
        return None

    def reset(self):
        self.canvas.destroy()
        self.create_widgets()

    def create_widgets(self):
        OUTPUT_PATH = Path(__file__).parent
        ASSETS_PATH = OUTPUT_PATH / Path(r"C:\Users\amine\Downloads\Projects\Maria-Data\assets\frame0")


        def relative_to_assets(path: str) -> Path:
            return ASSETS_PATH / Path(path)

        self.root.geometry("692x531")
        self.root.configure(bg = "#C62B3E")


        self.canvas = Canvas(
            self.root,
            bg = "#C62B3E",
            height = 531,
            width = 692,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )
        self.canvas.create_circle = self._create_circle

        self.canvas.place(x = 0, y = 0)
        self.button_image_1 = PhotoImage(
            file=relative_to_assets("button_1.png"))
        self.button_1 = Button(
            image=self.button_image_1,
            borderwidth=0,
            highlightthickness=0,
            command=self.load_volume_dicom,
            relief="flat"
        )
        self.button_1.place(
            x=455.0,
            y=52.0,
            width=175.0,
            height=76.0
        )

        self.button_image_2 = PhotoImage(
            file=relative_to_assets("button_2.png"))
        self.button_2 = Button(
            image=self.button_image_2,
            borderwidth=0,
            highlightthickness=0,
            command=self.show_viewer_in_background,
            relief="flat"
        )
        self.button_2.place(
            x=455.0,
            y=227.0,
            width=175.0,
            height=76.0
        )

        self.button_image_3 = PhotoImage(
            file=relative_to_assets("button_3.png"))
        self.button_3 = Button(
            image=self.button_image_3,
            borderwidth=0,
            highlightthickness=0,
            command=self.separate_bones_in_background,
            relief="flat"
        )
        self.button_3.place(
            x=455.0,
            y=402.0,
            width=175.0,
            height=76.0
        )

        self.button_image_4 = PhotoImage(
            file=relative_to_assets("button_4.png"))
        self.button_4 = Button(
            image=self.button_image_4,
            borderwidth=0,
            highlightthickness=0,
            command=self.view_snap_in_background,
            relief="flat"
        )
        self.button_4.place(
            x=63.0,
            y=402.0,
            width=175.0,
            height=76.0
        )


        self.button_image_5 = PhotoImage(
            file=relative_to_assets("button_5.png"))
        self.button_5 = Button(
            image=self.button_image_5,
            borderwidth=0,
            highlightthickness=0,
            command= self.slice_volume_in_background, #TODO
            relief="flat"
        )
        self.button_5.place(
            x=63.0,
            y=227.0,
            width=175.0,
            height=76.0
        )

        self.button_image_6 = PhotoImage(
            file=relative_to_assets("button_6.png"))
        self.button_6 = Button(
            image=self.button_image_6,
            borderwidth=0,
            highlightthickness=0,
            command=self.load_volume_in_background,
            relief="flat"
        )
        self.button_6.place(
            x=63.0,
            y=52.0,
            width=175.0,
            height=76.0
        )
        self.button_7 = Button(
            text = "Reset",
            borderwidth=0,
            highlightthickness=0,
            command=self.reset,
            relief="flat"
        )
        self.button_7.place(
            x=20.0,
            y=20.0,
            width=30.0,
            height=30.0
        )
        self.canvas.create_text(
            246.0,
            8.0,
            anchor="nw",
            text="Bone viz\n",
            fill="#000000",
            font=("Inter ExtraBold", 36 * -1)
        )
        self.root.mainloop()


if __name__ == '__main__':
    root = tk.Tk()
    app = ITKVolumeApp(root)
