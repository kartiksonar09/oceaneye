import { Spill, Suspect, Vessel } from '../types/api';
import { safeFormatTimestamp } from './core';

export interface ExportDossierOptions {
  spill?: Spill | null;
  vessel?: Vessel | null;
  suspects: Suspect[];
  vessels: Vessel[];
}

export async function exportDossierPdf({
  spill,
  vessel,
  suspects,
  vessels,
}: ExportDossierOptions): Promise<void> {
  const [{ default: jsPDF }, autoTableModule] = await Promise.all([
    import('jspdf'),
    import('jspdf-autotable'),
  ]);
  const autoTable = autoTableModule.default || autoTableModule;

  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
  });

  const pageWidth = doc.internal.pageSize.getWidth();

  const primaryColor = [15, 23, 42]; // Slate-900
  const accentAmber = [217, 119, 6]; // Amber-600
  const accentTeal = [13, 148, 136]; // Teal-600
  const borderGray = [226, 232, 240]; // Slate-200

  // 1. Top Header Banner
  doc.setFillColor(15, 23, 42);
  doc.rect(0, 0, pageWidth, 24, 'F');

  // Title
  doc.setTextColor(255, 255, 255);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(14);
  doc.text('OCEAN EYE // MARITIME INTELLIGENCE DOSSIER', 14, 11);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8);
  doc.setTextColor(148, 163, 184); // Slate-400
  doc.text('SAR OIL SLICK ATTRIBUTION & SENSOR TELEMETRY SYSTEM', 14, 17);

  // Classification Badge
  doc.setFillColor(220, 38, 38);
  doc.roundedRect(pageWidth - 48, 6, 34, 10, 1, 1, 'F');
  doc.setTextColor(255, 255, 255);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7);
  doc.text('CONFIDENTIAL', pageWidth - 44, 12.5);

  let currentY = 32;

  // Document Metadata Bar
  doc.setTextColor(100, 116, 139);
  doc.setFontSize(8);
  doc.text(`GENERATED: ${new Date().toISOString().replace('T', ' ').substring(0, 19)} UTC`, 14, currentY);
  doc.text(`REFERENCE ID: OE-DOS-${Date.now().toString(36).toUpperCase()}`, pageWidth - 70, currentY);
  currentY += 6;

  // Thin separator
  doc.setDrawColor(borderGray[0], borderGray[1], borderGray[2]);
  doc.line(14, currentY, pageWidth - 14, currentY);
  currentY += 8;

  // 2. Incident Spill Section (if present)
  if (spill) {
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(11);
    doc.setTextColor(primaryColor[0], primaryColor[1], primaryColor[2]);
    doc.text('1. SAR DETECTED OIL SLICK INCIDENT OVERVIEW', 14, currentY);
    currentY += 4;

    const spillData = [
      ['Spill Incident ID', spill.id],
      ['Current Status', spill.status.toUpperCase()],
      ['Satellite Sensor Source', spill.satellite_source],
      ['Detection Timestamp', safeFormatTimestamp(spill.detected_at)],
      ['Surface Slick Extent', `${spill.area_km2.toFixed(1)} km²`],
      ['Detection Algorithm Confidence', `${(spill.confidence * 100).toFixed(1)}%`],
      ['Centroid Coordinates', `${spill.centroid.lat.toFixed(5)}° N, ${spill.centroid.lng.toFixed(5)}° E`],
    ];

    autoTable(doc, {
      startY: currentY,
      head: [['Parameter', 'Operational Intelligence Value']],
      body: spillData,
      theme: 'grid',
      headStyles: { fillColor: [30, 41, 59], textColor: [255, 255, 255], fontStyle: 'bold', fontSize: 9 },
      bodyStyles: { fontSize: 8.5, textColor: [30, 41, 59] },
      columnStyles: {
        0: { cellWidth: 65, fontStyle: 'bold' },
        1: { cellWidth: 'auto' },
      },
      margin: { left: 14, right: 14 },
    });

    // @ts-expect-error jspdf-autotable extends jsPDF with lastAutoTable
    currentY = doc.lastAutoTable.finalY + 10;
  }

  // 3. Suspect Attribution Section
  const relevantSuspects = spill 
    ? suspects.filter(s => s.spill_id === spill.id)
    : vessel 
    ? suspects.filter(s => s.vessel_mmsi === vessel.mmsi)
    : [];

  if (relevantSuspects.length > 0) {
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(11);
    doc.setTextColor(220, 38, 38); // Red
    doc.text('2. DRIFT MODEL & CORRELATION ATTRIBUTION SUSPECTS', 14, currentY);
    currentY += 4;

    const suspectRows = relevantSuspects.map((s) => {
      const matchVessel = vessels.find((v) => v.mmsi === s.vessel_mmsi) || vessel;
      return [
        matchVessel?.name || 'UNKNOWN',
        s.vessel_mmsi,
        matchVessel?.flag || 'N/A',
        matchVessel?.vessel_type || 'N/A',
        matchVessel?.ais_gap_minutes ? `${matchVessel.ais_gap_minutes} MIN DARK` : 'NONE',
        `${(s.suspicion_score * 100).toFixed(1)}%`,
      ];
    });

    autoTable(doc, {
      startY: currentY,
      head: [['Vessel Name', 'MMSI', 'Flag', 'Type', 'AIS Gap', 'Attribution Score']],
      body: suspectRows,
      theme: 'grid',
      headStyles: { fillColor: [185, 28, 28], textColor: [255, 255, 255], fontStyle: 'bold', fontSize: 8.5 },
      bodyStyles: { fontSize: 8, textColor: [30, 41, 59] },
      margin: { left: 14, right: 14 },
    });

    // @ts-expect-error jspdf-autotable
    currentY = doc.lastAutoTable.finalY + 8;

    // Investigative Reasoning Points
    relevantSuspects.forEach((s) => {
      const matchVessel = vessels.find((v) => v.mmsi === s.vessel_mmsi) || vessel;
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(9);
      doc.setTextColor(primaryColor[0], primaryColor[1], primaryColor[2]);
      doc.text(`Investigative Reasoning Criteria for ${matchVessel?.name || s.vessel_mmsi}:`, 14, currentY);
      currentY += 4.5;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8);
      doc.setTextColor(51, 65, 85);
      s.reasoning.forEach((r) => {
        doc.text(`• ${r}`, 18, currentY);
        currentY += 4;
      });
      currentY += 4;
    });
  }

  // 4. Vessel Particulars Section (if vessel selected)
  if (vessel) {
    if (currentY > 210) {
      doc.addPage();
      currentY = 20;
    }

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(11);
    doc.setTextColor(primaryColor[0], primaryColor[1], primaryColor[2]);
    doc.text('3. VESSEL REGISTRY PARTICULARS & TELEMETRY', 14, currentY);
    currentY += 4;

    const vesselData = [
      ['Vessel Name', vessel.name],
      ['MMSI Number', vessel.mmsi],
      ['IMO / Call Sign', `${vessel.imo || 'UNKNOWN'} / ${vessel.call_sign || 'UNKNOWN'}`],
      ['Flag State', vessel.flag || 'UNKNOWN'],
      ['Vessel Classification', vessel.vessel_type],
      ['Dimensions & Draught', `${vessel.length_m || 'N/A'}m LOA × ${vessel.beam_m || 'N/A'}m Beam (Draught: ${vessel.draught_m || 'N/A'}m)`],
      ['Tonnage & Built Year', `${vessel.gross_tonnage ? `${vessel.gross_tonnage} GT` : 'N/A'} (Built: ${vessel.year_built || 'N/A'})`],
      ['Destination & ETA', `${vessel.destination || 'UNKNOWN'} (ETA: ${vessel.eta || 'UNKNOWN'})`],
      ['Current Kinematics', `${vessel.speed_knots.toFixed(1)} kt @ ${vessel.heading.toFixed(0)}° True Course`],
      ['AIS Transmission Integrity', vessel.ais_gap_minutes ? `DISCONTINUOUS — ${vessel.ais_gap_minutes} MIN GAP DETECTED` : 'CONTINUOUS (NO GAPS)'],
    ];

    autoTable(doc, {
      startY: currentY,
      head: [['Attribute', 'Vessel Record Details']],
      body: vesselData,
      theme: 'grid',
      headStyles: { fillColor: [13, 148, 136], textColor: [255, 255, 255], fontStyle: 'bold', fontSize: 9 },
      bodyStyles: { fontSize: 8.5, textColor: [30, 41, 59] },
      columnStyles: {
        0: { cellWidth: 65, fontStyle: 'bold' },
        1: { cellWidth: 'auto' },
      },
      margin: { left: 14, right: 14 },
    });

    // @ts-expect-error jspdf-autotable
    currentY = doc.lastAutoTable.finalY + 10;
  }

  // 5. Legal Disclaimer & Footer
  if (currentY > 245) {
    doc.addPage();
    currentY = 20;
  }

  doc.setFillColor(248, 250, 252);
  doc.rect(14, currentY, pageWidth - 28, 26, 'F');
  doc.setDrawColor(203, 213, 225);
  doc.rect(14, currentY, pageWidth - 28, 26, 'S');

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7.5);
  doc.setTextColor(71, 85, 105);
  doc.text('LEGAL NOTIFICATION & DECISION SUPPORT DISCLAIMER:', 18, currentY + 6);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7);
  doc.setTextColor(100, 116, 139);
  const disclaimer = 
    'Attribution scores and spatio-temporal back-trace vectors are calculated using synthetic aperture radar (SAR) ' +
    'signatures cross-referenced with AIS telemetry and hydrodynamic ocean current models. These scores provide operational ' +
    'prioritization guidance for maritime authorities and do NOT constitute legal proof or judicial determination of fault.';
  doc.text(doc.splitTextToSize(disclaimer, pageWidth - 36), 18, currentY + 12);

  // Page numbering on all pages
  const totalPages = doc.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.5);
    doc.setTextColor(148, 163, 184);
    doc.text(
      `Ocean Eye Intelligence Report • Page ${i} of ${totalPages} • Strictly Confidential`,
      pageWidth / 2,
      doc.internal.pageSize.getHeight() - 8,
      { align: 'center' }
    );
  }

  // Trigger download
  const filename = `OCEANEYE_DOSSIER_${spill?.id || vessel?.mmsi || 'INCIDENT'}_${Date.now()}.pdf`;
  doc.save(filename);
}
