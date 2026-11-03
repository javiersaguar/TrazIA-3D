/*
  Geometría del logo TrazIA 3D, trazada por caras desde docs/marca/trazia-3d-logo.png.
  Coordenadas en píxeles del PNG original (1254 × 1254). Cada cara conserva su degradado.
  Las caras negras de la T guardan un tono 0–1 para pintarlas en tinta (claro) o grafito (oscuro).
*/

export type LogoRole =
  | "t-top" | "t-front" | "t-end" | "t-inner" | "d-outer" | "d-arrow"
  | "w-T" | "w-r" | "w-a" | "w-z" | "w-I" | "w-A" | "w-3" | "w-D";

export type LogoFace = {
  role: LogoRole;
  d: string;
  /** Degradado en coordenadas del PNG: x1, y1, x2, y2. */
  g?: [number, number, number, number];
  /** Tono de tinta 0–1 en cada extremo (caras de la T). */
  ink?: [number, number];
  /** Colores fijos del celeste (caras de la D). */
  stops?: [string, string];
  /** Relleno plano del wordmark. */
  fill?: "word" | "sky";
};

export const MARK_VIEWBOX = "300 230 665 665";
export const WORD_VIEWBOX = "90 896 1075 154";
export const FULL_VIEWBOX = "90 230 1075 820";

export const LOGO_FACES: LogoFace[] = [
  { role: "d-outer", d: "M456 273 456 277 801 410 878 374 878 370 551 246Z", g: [651.9, 232.1, 690.5, 419.5], stops: ["#3cb7fc", "#95ddfc"] },
  { role: "d-outer", d: "M883 376 803 412 803 443 806 450 884 522 884 749 888 749 948 672 948 433 893 380Z", g: [806.2, 650.9, 959.4, 441.7], stops: ["#0790e9", "#6bd4ff"] },
  { role: "d-outer", d: "M852 492 847 492 848 653 847 658 816 689 816 762 698 825 698 829 732 834 884 754 883 521Z", g: [888.1, 681.5, 713.4, 693.4], stops: ["#035793", "#095d99"] },
  { role: "t-top", d: "M336 316 336 320 416 346 680 448 687 448 767 414 767 410 425 281 416 282Z", g: [577.1, 320.3, 529.6, 408.8], ink: [0.4, 0.96] },
  { role: "t-front", d: "M316 329 317 409 460 465 460 773 530 840 540 845 540 497 680 548 680 463 392 353Z", g: [376.3, 564.5, 665.6, 494.2], ink: [0.0, 0.9] },
  { role: "t-end", d: "M784 424 768 428 694 461 694 546 784 505Z", g: [696.5, 481.2, 781.2, 486.9], ink: [0.16, 0.35] },
  { role: "t-inner", d: "M554 516 554 738 559 738 606 711 606 536Z", g: [550.9, 623.2, 607.4, 627.6], ink: [0.09, 0.6] },
  { role: "d-arrow", d: "M631 608 631 612 729 663 758 650 765 639 774 639 775 635 798 629 798 624 697 573Z", g: [691.8, 576.7, 734.6, 658.6], stops: ["#007bd1", "#64d0ff"] },
  { role: "d-arrow", d: "M802 630 732 664 730 696 565 780 565 876 802 755Z", g: [597.4, 728.9, 776.0, 786.7], stops: ["#002f52", "#1aa1f0"] },
  { role: "w-T", d: "M101 906 101 934 157 935 157 1039 187 1039 187 935 244 934 245 907Z", fill: "word" },
  { role: "w-I", d: "M603 906 603 1039 633 1039 633 906Z", fill: "word" },
  { role: "w-A", d: "M644 1038 678 1039 730 947 782 1039 816 1039 740 906 720 906Z", fill: "word" },
  { role: "w-3", d: "M861 906 862 934 947 934 954 939 956 943 956 951 950 958 947 959 880 960 880 986 947 986 954 991 956 995 956 1003 954 1007 947 1012 856 1012 855 1039 956 1039 974 1031 980 1025 986 1011 985 988 980 979 974 973 983 961 986 949 985 933 979 920 970 912 962 908 952 906Z", fill: "sky" },
  { role: "w-D", d: "M1002 907 1002 1039 1104 1039 1127 1030 1141 1017 1147 1007 1152 991 1153 960 1145 935 1129 917 1118 911 1100 906Z M1033 936 1035 934 1094 934 1109 939 1118 949 1122 960 1122 986 1116 1000 1107 1008 1098 1011 1034 1011Z", fill: "sky" },
  { role: "w-r", d: "M335 937 272 937 261 940 250 948 243 964 243 1039 271 1038 272 968 280 962 335 962Z", fill: "word" },
  { role: "w-a", d: "M350 938 351 962 431 962 437 967 438 975 357 977 348 981 342 987 338 997 339 1023 348 1035 358 1039 466 1038 466 966 463 954 455 944 446 939 437 937Z M365 1004 372 998 437 998 438 1015 370 1016 365 1010Z", fill: "word" },
  { role: "w-z", d: "M481 937 481 962 543 963 480 1016 480 1039 587 1039 587 1015 523 1014 587 961 587 937Z", fill: "word" },
];
