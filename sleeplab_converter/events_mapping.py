from typing import Dict

from sleeplab_format import models

STAGE_MAPPING: Dict = {
    # Deltamed
    "Veille": models.AASMSleepStage.W,
    "Stade 1": models.AASMSleepStage.N1,
    "Stade 2": models.AASMSleepStage.N2,
    "Stade 3": models.AASMSleepStage.N3,
    "Stade 4": models.AASMSleepStage.N3,  # RK stage 4 combined to 3 in AASM rules
    "S. Paradoxal": models.AASMSleepStage.R,
    "Indéterminé": models.AASMSleepStage.UNSCORED,
    # Remlogic
    "SLEEP-S0": models.AASMSleepStage.W,
    "SLEEP-S1": models.AASMSleepStage.N1,
    "SLEEP-S2": models.AASMSleepStage.N2,
    "SLEEP-S3": models.AASMSleepStage.N3,
    "SLEEP-S4": models.AASMSleepStage.N3,  # RK stage 4 combined to 3 in AASM rules
    "SLEEP-REM": models.AASMSleepStage.R,
    # BrainRT
    "Sleep stage W": models.AASMSleepStage.W,
    "Sleep stage N1": models.AASMSleepStage.N1,
    "Sleep stage N2": models.AASMSleepStage.N2,
    "Sleep stage N3": models.AASMSleepStage.N3,
    "Sleep stage N4": models.AASMSleepStage.N3,  # RK stage 4 combined to 3 in AASM rules
    "Sleep stage R": models.AASMSleepStage.R,
    "SLEEP-UNSCORED": models.AASMSleepStage.UNSCORED,
}

# Score all artifacts as ARTIFACT
# Deltamed exports channel-specific artefacts like 'Artefact (PRES)', check 'original_annotations.a' -file for these
AASM_EVENT_MAPPING: Dict = {
    #'': models.AASMEvent.UNSURE,
    "SIGNAL-ARTIFACT": models.AASMEvent.ARTIFACT,  # Remlogic
    "SIGNAL-QUALITY-LOW": models.AASMEvent.ARTIFACT,  # Remlogic
    "PLM droit": models.AASMEvent.PLM_RIGHT,  # Deltamed
    "PLM Gauce": models.AASMEvent.PLM_LEFT,  # Deltamed
    "PLM-LM": models.AASMEvent.PLM,  # Remlogic
    "PLM": models.AASMEvent.PLM,  # Remlogic
    "Limb movement : Mouvement de la jambe gauche": models.AASMEvent.PLM,  # csv
    "Arousal non spécifique": models.AASMEvent.AROUSAL,  # Deltamed
    "Arousal cortical": models.AASMEvent.AROUSAL,  # Deltamed
    "AROUSAL": models.AASMEvent.AROUSAL,  # Remlogic
    "Micro-éveil": models.AASMEvent.AROUSAL,  # csv #This is arousal also (manually scored)
    "Arousal d'origine respiratoire": models.AASMEvent.AROUSAL_RES,  # Deltamed
    "AROUSAL-RESP": models.AASMEvent.AROUSAL_RES,  # Remlogic
    "AROUSAL-SNORE": models.AASMEvent.AROUSAL_RES,  # Remlogic
    "AROUSAL-HYPOPNEA": models.AASMEvent.AROUSAL_RES,  # Remlogic
    "AROUSAL-APNEA": models.AASMEvent.AROUSAL_RES,  # Remlogic
    "AROUSAL-DESAT": models.AASMEvent.AROUSAL_RES,  # Remlogic
    "AROUSAL-SPONT": models.AASMEvent.AROUSAL_SPONT,  # Remlogic
    "Arousal autonome": models.AASMEvent.AROUSAL_SPONT,  # Remlogic
    "AROUSAL-PLM": models.AASMEvent.AROUSAL_PLM,  # Remlogic
    "Mouvement + arousal": models.AASMEvent.AROUSAL_LM,  # Deltamed
    "AROUSAL-LM": models.AASMEvent.AROUSAL_LM,  # Remlogic
    "AROUSAL-RERA": models.AASMEvent.RERA,
    "Apnée": models.AASMEvent.APNEA,  # Deltamed
    "APNEA": models.AASMEvent.APNEA,  # Remlogic
    "Apnée Centrale": models.AASMEvent.APNEA_CENTRAL,  # Deltamed
    "APNEA-CENTRAL": models.AASMEvent.APNEA_CENTRAL,  # Remlogic
    "Apnée centrale": models.AASMEvent.APNEA_CENTRAL,  # csv
    "Apnée Obstructive": models.AASMEvent.APNEA_OBSTRUCTIVE,  # Deltamed
    "APNEA-OBSTRUCTIVE": models.AASMEvent.APNEA_OBSTRUCTIVE,  # Remlogic
    "Apnée obstructive": models.AASMEvent.APNEA_OBSTRUCTIVE,  # csv
    "Apnée Mixte": models.AASMEvent.APNEA_MIXED,  # Deltamed
    "APNEA-MIXED": models.AASMEvent.APNEA_MIXED,  # Remlogic
    "Apnée mixte": models.AASMEvent.APNEA_MIXED,  # Remlogic
    #'Hypopnée': models.AASMEvent.HYPOPNEA, # Deltamed - This is obstructive by default (confirmed by Marion from sleep lab)
    "HYPOPNEA": models.AASMEvent.HYPOPNEA,  # Remlogic - These are unclassified hypopneas (confirmed by Marion from sleep lab)
    "hypopnée": models.AASMEvent.HYPOPNEA,  # csv
    "hypopnée Centrale": models.AASMEvent.HYPOPNEA_CENTRAL,  # Deltamed
    "HYPOPNEA-CENTRAL": models.AASMEvent.HYPOPNEA_CENTRAL,  # Remlogic
    "Hypopnée centrale": models.AASMEvent.HYPOPNEA_CENTRAL,  # csv
    "Hypopnée": models.AASMEvent.HYPOPNEA_OBSTRUCTIVE,  # Deltamed - This is obstructive by default (confirmed by Marion from sleep lab)
    "HYPOPNEA-OBSTRUCTIVE": models.AASMEvent.HYPOPNEA_OBSTRUCTIVE,  # Remlogic
    "hypopnée Obstructive": models.AASMEvent.HYPOPNEA_OBSTRUCTIVE,  # Deltamed
    "Hypopnée obstructive": models.AASMEvent.HYPOPNEA_OBSTRUCTIVE,  # csv
    # There are also mixed hypopneas scored in the data 'Hypopnée Mixte' check all annotation file for these
    # because sleeplab format does not support this as an AASMEvent currently
    # Should we group these into HYPOPNEA? Only around 20 found in the whole dataset
    #'Désaturation': models.AASMEvent.SPO2_DESAT, #Deltamed # UPDATE: this is automatic scoring
    #'DESAT': models.AASMEvent.SPO2_DESAT, #Remlogic # UPDATE: this is automatic scoring
    "Chute de la saturation": models.AASMEvent.SPO2_DESAT,  # csv
    #'Ronflements simples':models.AASMEvent.SNORE, #Deltamed UPDATE: this is automatic scoring
    #'SNORE-SINGLE':models.AASMEvent.SNORE, #Remlogic # UPDATE: this is automatic scoring
    "Périodes de ronflement": models.AASMEvent.SNORE,  # csv
}
