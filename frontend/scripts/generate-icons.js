const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const sizes = {
  'favicon.ico': [16, 32],
  'icon.png': [32],
  'apple-icon.png': [180]
};

async function generateIcons() {
  const svgBuffer = fs.readFileSync(path.join(__dirname, '../public/favicon.svg'));
  
  for (const [filename, dimensions] of Object.entries(sizes)) {
    const outputPath = path.join(__dirname, '../public', filename);
    
    if (filename.endsWith('.ico')) {
      // Generate ICO file
      const pngBuffers = await Promise.all(
        dimensions.map(size =>
          sharp(svgBuffer)
            .resize(size, size)
            .png()
            .toBuffer()
        )
      );
      
      // Combine PNGs into ICO
      const ico = require('sharp-ico');
      const icoBuffer = await ico.create(pngBuffers);
      fs.writeFileSync(outputPath, icoBuffer);
    } else {
      // Generate PNG files
      await sharp(svgBuffer)
        .resize(dimensions[0], dimensions[0])
        .png()
        .toFile(outputPath);
    }
    
    console.log(`Generated ${filename}`);
  }
}

generateIcons().catch(console.error); 