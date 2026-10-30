import BetaKit
import PhotosUI
import SwiftUI
import UIKit

struct CaptureView: View {
    @Environment(AppModel.self) private var model
    @State private var pickerItem: PhotosPickerItem?
    @State private var showCamera = false
    @State private var knowsWallHeight = false
    @State private var wallHeight: Double = 450

    var body: some View {
        VStack(spacing: 20) {
            Spacer()
            Image(systemName: "camera.viewfinder")
                .font(.system(size: 72))
                .foregroundStyle(Color.accentOrange)
            Text("Photograph the problem")
                .font(.title.bold())
            Text("Stand back so the whole problem, from the start holds to the top, is in frame.")
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Toggle("I know the wall height", isOn: $knowsWallHeight)
            if knowsWallHeight {
                Stepper("Wall height: \(Int(wallHeight)) cm", value: $wallHeight, in: 250...700, step: 10)
            }
            Spacer()
            if UIImagePickerController.isSourceTypeAvailable(.camera) {
                Button {
                    showCamera = true
                } label: {
                    Label("Take photo", systemImage: "camera").frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
            }
            PhotosPicker(selection: $pickerItem, matching: .images) {
                Label("Choose from library", systemImage: "photo.on.rectangle").frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)
        }
        .padding()
        .onChange(of: pickerItem) { _, item in
            guard let item else { return }
            Task {
                if let data = try? await item.loadTransferable(type: Data.self), let image = UIImage(data: data) {
                    await submit(image)
                }
            }
        }
        .fullScreenCover(isPresented: $showCamera) {
            CameraPicker { image in
                Task { await submit(image) }
            }
            .ignoresSafeArea()
        }
    }

    private func submit(_ image: UIImage) async {
        guard let jpeg = image.preparedForUpload() else { return }
        await model.session.upload(jpeg: jpeg, wallHeightCm: knowsWallHeight ? wallHeight : nil)
    }
}

extension UIImage {
    /// Upright (orientation applied), at most `maxSide` pixels, JPEG. HEIC never leaves the phone.
    func preparedForUpload(maxSide: CGFloat = 2048) -> Data? {
        let scale = min(1, maxSide / max(size.width, size.height))
        let target = CGSize(width: size.width * scale, height: size.height * scale)
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        let resized = UIGraphicsImageRenderer(size: target, format: format).image { _ in
            draw(in: CGRect(origin: .zero, size: target))
        }
        return resized.jpegData(compressionQuality: 0.85)
    }
}

struct CameraPicker: UIViewControllerRepresentable {
    let onImage: (UIImage) -> Void
    @Environment(\.dismiss) private var dismiss

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = .camera
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ controller: UIImagePickerController, context: Context) {}

    func makeCoordinator() -> Coordinator { Coordinator(parent: self) }

    final class Coordinator: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let parent: CameraPicker

        init(parent: CameraPicker) { self.parent = parent }

        func imagePickerController(
            _ picker: UIImagePickerController,
            didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]
        ) {
            if let image = info[.originalImage] as? UIImage { parent.onImage(image) }
            parent.dismiss()
        }

        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            parent.dismiss()
        }
    }
}
