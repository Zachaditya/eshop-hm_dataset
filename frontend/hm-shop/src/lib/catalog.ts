export const MODE_TO_INDEX_GROUPS: Record<"men" | "women", string[]> = {
    men: ["Menswear"],
    women: ["Ladieswear", "Divided"],
  };
  
  export const CATEGORY_TO_PRODUCT_GROUPS: Record<string, string[]> = {
    clothing: [
      "Garment Upper body",
      "Garment Lower body",
      "Garment Full body",
      "Underwear",
      "Socks & Tights",
      "Swimwear",
      "Nightwear",
    ],
    footwear: ["Shoes"],
    accessories: ["Accessories", "Bags"],
    lifestyle: ["Items", "Furniture", "Stationery", "Garment and Shoe care"],
    other: [], // show all groups for that mode
  };
  