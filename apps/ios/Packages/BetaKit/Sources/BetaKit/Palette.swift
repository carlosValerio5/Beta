import Foundation

/// Mirrors contracts/palette.json (checked by ContractDecodingTests).
public enum Palette {
    public static let limbHex: [Limb: String] = [
        .lh: "#3B82F6",
        .rh: "#EF4444",
        .lf: "#14B8A6",
        .rf: "#F97316",
    ]
    public static let holdHex: [String: String] = [
        "red": "#D22828",
        "orange": "#F0781E",
        "yellow": "#F0C81E",
        "green": "#28AA46",
        "blue": "#285AD2",
        "purple": "#823CB4",
        "pink": "#E65AA0",
    ]
    public static let accentHex = "#FF6B35"
    public static let inkHex = "#0F1115"
    public static let chalkHex = "#F5F3EE"

    /// Components in 0...1 for a "#RRGGBB" string (black for anything malformed).
    public static func rgb(_ hex: String) -> (red: Double, green: Double, blue: Double) {
        let digits = hex.hasPrefix("#") ? String(hex.dropFirst()) : hex
        guard digits.count == 6, let value = UInt32(digits, radix: 16) else { return (0, 0, 0) }
        return (
            Double((value >> 16) & 0xFF) / 255,
            Double((value >> 8) & 0xFF) / 255,
            Double(value & 0xFF) / 255
        )
    }
}
