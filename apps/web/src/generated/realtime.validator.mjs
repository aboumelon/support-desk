// Generated from contracts/realtime.schema.json. Do not edit.
import runtime0 from "ajv/dist/runtime/ucs2length.js";
("use strict");
export const validate = validate10;
export default validate10;
const schema11 = {
  $defs: {
    AiDelta: {
      properties: {
        attempt: { maximum: 3, minimum: 1, title: "Attempt", type: "integer" },
        chunk_index: { minimum: 0, title: "Chunk Index", type: "integer" },
        control_epoch: { minimum: 0, title: "Control Epoch", type: "integer" },
        conversation_id: {
          format: "uuid",
          title: "Conversation Id",
          type: "string",
        },
        protocol_version: {
          const: 1,
          default: 1,
          title: "Protocol Version",
          type: "integer",
        },
        run_id: { format: "uuid", title: "Run Id", type: "string" },
        text: { maxLength: 8000, title: "Text", type: "string" },
        type: { const: "ai.delta", title: "Type", type: "string" },
      },
      required: [
        "type",
        "conversation_id",
        "run_id",
        "control_epoch",
        "attempt",
        "chunk_index",
        "text",
      ],
      title: "AiDelta",
      type: "object",
    },
    DurableEvent: {
      properties: {
        conversation_id: {
          format: "uuid",
          title: "Conversation Id",
          type: "string",
        },
        data: {
          additionalProperties: {
            anyOf: [
              { type: "string" },
              { type: "integer" },
              { type: "boolean" },
              { type: "null" },
            ],
          },
          title: "Data",
          type: "object",
        },
        event_id: { format: "uuid", title: "Event Id", type: "string" },
        occurred_at: {
          format: "date-time",
          title: "Occurred At",
          type: "string",
        },
        protocol_version: {
          const: 1,
          default: 1,
          title: "Protocol Version",
          type: "integer",
        },
        seq: { minimum: 1, title: "Seq", type: "integer" },
        type: {
          enum: [
            "conversation.created",
            "message.created",
            "conversation.control_changed",
            "conversation.resolved",
            "conversation.reopened",
            "read_cursor.updated",
            "ai.run_changed",
          ],
          title: "Type",
          type: "string",
        },
      },
      required: [
        "type",
        "event_id",
        "conversation_id",
        "seq",
        "occurred_at",
        "data",
      ],
      title: "DurableEvent",
      type: "object",
    },
    PresenceUpdate: {
      properties: {
        actor_id: { format: "uuid", title: "Actor Id", type: "string" },
        conversation_id: {
          format: "uuid",
          title: "Conversation Id",
          type: "string",
        },
        online: { title: "Online", type: "boolean" },
        protocol_version: {
          const: 1,
          default: 1,
          title: "Protocol Version",
          type: "integer",
        },
        type: { const: "presence.updated", title: "Type", type: "string" },
      },
      required: ["type", "conversation_id", "actor_id", "online"],
      title: "PresenceUpdate",
      type: "object",
    },
    TypingUpdate: {
      properties: {
        actor_id: { format: "uuid", title: "Actor Id", type: "string" },
        conversation_id: {
          format: "uuid",
          title: "Conversation Id",
          type: "string",
        },
        expires_in: {
          const: 5,
          default: 5,
          title: "Expires In",
          type: "integer",
        },
        protocol_version: {
          const: 1,
          default: 1,
          title: "Protocol Version",
          type: "integer",
        },
        type: { const: "typing.updated", title: "Type", type: "string" },
      },
      required: ["type", "conversation_id", "actor_id"],
      title: "TypingUpdate",
      type: "object",
    },
  },
  anyOf: [
    { $ref: "#/$defs/DurableEvent" },
    { $ref: "#/$defs/AiDelta" },
    { $ref: "#/$defs/TypingUpdate" },
    { $ref: "#/$defs/PresenceUpdate" },
  ],
  title: "RealtimeFrame",
};
const schema12 = {
  properties: {
    conversation_id: {
      format: "uuid",
      title: "Conversation Id",
      type: "string",
    },
    data: {
      additionalProperties: {
        anyOf: [
          { type: "string" },
          { type: "integer" },
          { type: "boolean" },
          { type: "null" },
        ],
      },
      title: "Data",
      type: "object",
    },
    event_id: { format: "uuid", title: "Event Id", type: "string" },
    occurred_at: { format: "date-time", title: "Occurred At", type: "string" },
    protocol_version: {
      const: 1,
      default: 1,
      title: "Protocol Version",
      type: "integer",
    },
    seq: { minimum: 1, title: "Seq", type: "integer" },
    type: {
      enum: [
        "conversation.created",
        "message.created",
        "conversation.control_changed",
        "conversation.resolved",
        "conversation.reopened",
        "read_cursor.updated",
        "ai.run_changed",
      ],
      title: "Type",
      type: "string",
    },
  },
  required: [
    "type",
    "event_id",
    "conversation_id",
    "seq",
    "occurred_at",
    "data",
  ],
  title: "DurableEvent",
  type: "object",
};
const schema13 = {
  properties: {
    attempt: { maximum: 3, minimum: 1, title: "Attempt", type: "integer" },
    chunk_index: { minimum: 0, title: "Chunk Index", type: "integer" },
    control_epoch: { minimum: 0, title: "Control Epoch", type: "integer" },
    conversation_id: {
      format: "uuid",
      title: "Conversation Id",
      type: "string",
    },
    protocol_version: {
      const: 1,
      default: 1,
      title: "Protocol Version",
      type: "integer",
    },
    run_id: { format: "uuid", title: "Run Id", type: "string" },
    text: { maxLength: 8000, title: "Text", type: "string" },
    type: { const: "ai.delta", title: "Type", type: "string" },
  },
  required: [
    "type",
    "conversation_id",
    "run_id",
    "control_epoch",
    "attempt",
    "chunk_index",
    "text",
  ],
  title: "AiDelta",
  type: "object",
};
const schema14 = {
  properties: {
    actor_id: { format: "uuid", title: "Actor Id", type: "string" },
    conversation_id: {
      format: "uuid",
      title: "Conversation Id",
      type: "string",
    },
    expires_in: { const: 5, default: 5, title: "Expires In", type: "integer" },
    protocol_version: {
      const: 1,
      default: 1,
      title: "Protocol Version",
      type: "integer",
    },
    type: { const: "typing.updated", title: "Type", type: "string" },
  },
  required: ["type", "conversation_id", "actor_id"],
  title: "TypingUpdate",
  type: "object",
};
const schema15 = {
  properties: {
    actor_id: { format: "uuid", title: "Actor Id", type: "string" },
    conversation_id: {
      format: "uuid",
      title: "Conversation Id",
      type: "string",
    },
    online: { title: "Online", type: "boolean" },
    protocol_version: {
      const: 1,
      default: 1,
      title: "Protocol Version",
      type: "integer",
    },
    type: { const: "presence.updated", title: "Type", type: "string" },
  },
  required: ["type", "conversation_id", "actor_id", "online"],
  title: "PresenceUpdate",
  type: "object",
};
const func2 = runtime0.default ?? runtime0;

function validate10(
  data,
  { instancePath = "", parentData, parentDataProperty, rootData = data } = {},
) {
  let vErrors = null;
  let errors = 0;
  const _errs0 = errors;
  let valid0 = false;
  const _errs1 = errors;
  const _errs2 = errors;
  if (errors === _errs2) {
    if (data && typeof data == "object" && !Array.isArray(data)) {
      let missing0;
      if (
        (data.type === undefined && (missing0 = "type")) ||
        (data.event_id === undefined && (missing0 = "event_id")) ||
        (data.conversation_id === undefined &&
          (missing0 = "conversation_id")) ||
        (data.seq === undefined && (missing0 = "seq")) ||
        (data.occurred_at === undefined && (missing0 = "occurred_at")) ||
        (data.data === undefined && (missing0 = "data"))
      ) {
        const err0 = {
          instancePath,
          schemaPath: "#/$defs/DurableEvent/required",
          keyword: "required",
          params: { missingProperty: missing0 },
          message: "must have required property '" + missing0 + "'",
        };
        if (vErrors === null) {
          vErrors = [err0];
        } else {
          vErrors.push(err0);
        }
        errors++;
      } else {
        if (data.conversation_id !== undefined) {
          const _errs4 = errors;
          if (errors === _errs4) {
            if (errors === _errs4) {
              if (!(typeof data.conversation_id === "string")) {
                const err1 = {
                  instancePath: instancePath + "/conversation_id",
                  schemaPath:
                    "#/$defs/DurableEvent/properties/conversation_id/type",
                  keyword: "type",
                  params: { type: "string" },
                  message: "must be string",
                };
                if (vErrors === null) {
                  vErrors = [err1];
                } else {
                  vErrors.push(err1);
                }
                errors++;
              }
            }
          }
          var valid2 = _errs4 === errors;
        } else {
          var valid2 = true;
        }
        if (valid2) {
          if (data.data !== undefined) {
            let data1 = data.data;
            const _errs6 = errors;
            if (errors === _errs6) {
              if (data1 && typeof data1 == "object" && !Array.isArray(data1)) {
                for (const key0 in data1) {
                  let data2 = data1[key0];
                  const _errs9 = errors;
                  const _errs10 = errors;
                  let valid4 = false;
                  const _errs11 = errors;
                  if (typeof data2 !== "string") {
                    const err2 = {
                      instancePath:
                        instancePath +
                        "/data/" +
                        key0.replace(/~/g, "~0").replace(/\//g, "~1"),
                      schemaPath:
                        "#/$defs/DurableEvent/properties/data/additionalProperties/anyOf/0/type",
                      keyword: "type",
                      params: { type: "string" },
                      message: "must be string",
                    };
                    if (vErrors === null) {
                      vErrors = [err2];
                    } else {
                      vErrors.push(err2);
                    }
                    errors++;
                  }
                  var _valid1 = _errs11 === errors;
                  valid4 = valid4 || _valid1;
                  if (!valid4) {
                    const _errs13 = errors;
                    if (!(
                      typeof data2 == "number" &&
                      !(data2 % 1) &&
                      !isNaN(data2)
                    )) {
                      const err3 = {
                        instancePath:
                          instancePath +
                          "/data/" +
                          key0.replace(/~/g, "~0").replace(/\//g, "~1"),
                        schemaPath:
                          "#/$defs/DurableEvent/properties/data/additionalProperties/anyOf/1/type",
                        keyword: "type",
                        params: { type: "integer" },
                        message: "must be integer",
                      };
                      if (vErrors === null) {
                        vErrors = [err3];
                      } else {
                        vErrors.push(err3);
                      }
                      errors++;
                    }
                    var _valid1 = _errs13 === errors;
                    valid4 = valid4 || _valid1;
                    if (!valid4) {
                      const _errs15 = errors;
                      if (typeof data2 !== "boolean") {
                        const err4 = {
                          instancePath:
                            instancePath +
                            "/data/" +
                            key0.replace(/~/g, "~0").replace(/\//g, "~1"),
                          schemaPath:
                            "#/$defs/DurableEvent/properties/data/additionalProperties/anyOf/2/type",
                          keyword: "type",
                          params: { type: "boolean" },
                          message: "must be boolean",
                        };
                        if (vErrors === null) {
                          vErrors = [err4];
                        } else {
                          vErrors.push(err4);
                        }
                        errors++;
                      }
                      var _valid1 = _errs15 === errors;
                      valid4 = valid4 || _valid1;
                      if (!valid4) {
                        const _errs17 = errors;
                        if (data2 !== null) {
                          const err5 = {
                            instancePath:
                              instancePath +
                              "/data/" +
                              key0.replace(/~/g, "~0").replace(/\//g, "~1"),
                            schemaPath:
                              "#/$defs/DurableEvent/properties/data/additionalProperties/anyOf/3/type",
                            keyword: "type",
                            params: { type: "null" },
                            message: "must be null",
                          };
                          if (vErrors === null) {
                            vErrors = [err5];
                          } else {
                            vErrors.push(err5);
                          }
                          errors++;
                        }
                        var _valid1 = _errs17 === errors;
                        valid4 = valid4 || _valid1;
                      }
                    }
                  }
                  if (!valid4) {
                    const err6 = {
                      instancePath:
                        instancePath +
                        "/data/" +
                        key0.replace(/~/g, "~0").replace(/\//g, "~1"),
                      schemaPath:
                        "#/$defs/DurableEvent/properties/data/additionalProperties/anyOf",
                      keyword: "anyOf",
                      params: {},
                      message: "must match a schema in anyOf",
                    };
                    if (vErrors === null) {
                      vErrors = [err6];
                    } else {
                      vErrors.push(err6);
                    }
                    errors++;
                  } else {
                    errors = _errs10;
                    if (vErrors !== null) {
                      if (_errs10) {
                        vErrors.length = _errs10;
                      } else {
                        vErrors = null;
                      }
                    }
                  }
                  var valid3 = _errs9 === errors;
                  if (!valid3) {
                    break;
                  }
                }
              } else {
                const err7 = {
                  instancePath: instancePath + "/data",
                  schemaPath: "#/$defs/DurableEvent/properties/data/type",
                  keyword: "type",
                  params: { type: "object" },
                  message: "must be object",
                };
                if (vErrors === null) {
                  vErrors = [err7];
                } else {
                  vErrors.push(err7);
                }
                errors++;
              }
            }
            var valid2 = _errs6 === errors;
          } else {
            var valid2 = true;
          }
          if (valid2) {
            if (data.event_id !== undefined) {
              const _errs19 = errors;
              if (errors === _errs19) {
                if (errors === _errs19) {
                  if (!(typeof data.event_id === "string")) {
                    const err8 = {
                      instancePath: instancePath + "/event_id",
                      schemaPath:
                        "#/$defs/DurableEvent/properties/event_id/type",
                      keyword: "type",
                      params: { type: "string" },
                      message: "must be string",
                    };
                    if (vErrors === null) {
                      vErrors = [err8];
                    } else {
                      vErrors.push(err8);
                    }
                    errors++;
                  }
                }
              }
              var valid2 = _errs19 === errors;
            } else {
              var valid2 = true;
            }
            if (valid2) {
              if (data.occurred_at !== undefined) {
                const _errs21 = errors;
                if (errors === _errs21) {
                  if (errors === _errs21) {
                    if (!(typeof data.occurred_at === "string")) {
                      const err9 = {
                        instancePath: instancePath + "/occurred_at",
                        schemaPath:
                          "#/$defs/DurableEvent/properties/occurred_at/type",
                        keyword: "type",
                        params: { type: "string" },
                        message: "must be string",
                      };
                      if (vErrors === null) {
                        vErrors = [err9];
                      } else {
                        vErrors.push(err9);
                      }
                      errors++;
                    }
                  }
                }
                var valid2 = _errs21 === errors;
              } else {
                var valid2 = true;
              }
              if (valid2) {
                if (data.protocol_version !== undefined) {
                  let data5 = data.protocol_version;
                  const _errs23 = errors;
                  if (!(
                    typeof data5 == "number" &&
                    !(data5 % 1) &&
                    !isNaN(data5)
                  )) {
                    const err10 = {
                      instancePath: instancePath + "/protocol_version",
                      schemaPath:
                        "#/$defs/DurableEvent/properties/protocol_version/type",
                      keyword: "type",
                      params: { type: "integer" },
                      message: "must be integer",
                    };
                    if (vErrors === null) {
                      vErrors = [err10];
                    } else {
                      vErrors.push(err10);
                    }
                    errors++;
                  }
                  if (1 !== data5) {
                    const err11 = {
                      instancePath: instancePath + "/protocol_version",
                      schemaPath:
                        "#/$defs/DurableEvent/properties/protocol_version/const",
                      keyword: "const",
                      params: { allowedValue: 1 },
                      message: "must be equal to constant",
                    };
                    if (vErrors === null) {
                      vErrors = [err11];
                    } else {
                      vErrors.push(err11);
                    }
                    errors++;
                  }
                  var valid2 = _errs23 === errors;
                } else {
                  var valid2 = true;
                }
                if (valid2) {
                  if (data.seq !== undefined) {
                    let data6 = data.seq;
                    const _errs25 = errors;
                    if (!(
                      typeof data6 == "number" &&
                      !(data6 % 1) &&
                      !isNaN(data6)
                    )) {
                      const err12 = {
                        instancePath: instancePath + "/seq",
                        schemaPath: "#/$defs/DurableEvent/properties/seq/type",
                        keyword: "type",
                        params: { type: "integer" },
                        message: "must be integer",
                      };
                      if (vErrors === null) {
                        vErrors = [err12];
                      } else {
                        vErrors.push(err12);
                      }
                      errors++;
                    }
                    if (errors === _errs25) {
                      if (typeof data6 == "number") {
                        if (data6 < 1 || isNaN(data6)) {
                          const err13 = {
                            instancePath: instancePath + "/seq",
                            schemaPath:
                              "#/$defs/DurableEvent/properties/seq/minimum",
                            keyword: "minimum",
                            params: { comparison: ">=", limit: 1 },
                            message: "must be >= 1",
                          };
                          if (vErrors === null) {
                            vErrors = [err13];
                          } else {
                            vErrors.push(err13);
                          }
                          errors++;
                        }
                      }
                    }
                    var valid2 = _errs25 === errors;
                  } else {
                    var valid2 = true;
                  }
                  if (valid2) {
                    if (data.type !== undefined) {
                      let data7 = data.type;
                      const _errs27 = errors;
                      if (typeof data7 !== "string") {
                        const err14 = {
                          instancePath: instancePath + "/type",
                          schemaPath:
                            "#/$defs/DurableEvent/properties/type/type",
                          keyword: "type",
                          params: { type: "string" },
                          message: "must be string",
                        };
                        if (vErrors === null) {
                          vErrors = [err14];
                        } else {
                          vErrors.push(err14);
                        }
                        errors++;
                      }
                      if (!(
                        data7 === "conversation.created" ||
                        data7 === "message.created" ||
                        data7 === "conversation.control_changed" ||
                        data7 === "conversation.resolved" ||
                        data7 === "conversation.reopened" ||
                        data7 === "read_cursor.updated" ||
                        data7 === "ai.run_changed"
                      )) {
                        const err15 = {
                          instancePath: instancePath + "/type",
                          schemaPath:
                            "#/$defs/DurableEvent/properties/type/enum",
                          keyword: "enum",
                          params: {
                            allowedValues: schema12.properties.type.enum,
                          },
                          message: "must be equal to one of the allowed values",
                        };
                        if (vErrors === null) {
                          vErrors = [err15];
                        } else {
                          vErrors.push(err15);
                        }
                        errors++;
                      }
                      var valid2 = _errs27 === errors;
                    } else {
                      var valid2 = true;
                    }
                  }
                }
              }
            }
          }
        }
      }
    } else {
      const err16 = {
        instancePath,
        schemaPath: "#/$defs/DurableEvent/type",
        keyword: "type",
        params: { type: "object" },
        message: "must be object",
      };
      if (vErrors === null) {
        vErrors = [err16];
      } else {
        vErrors.push(err16);
      }
      errors++;
    }
  }
  var _valid0 = _errs1 === errors;
  valid0 = valid0 || _valid0;
  if (!valid0) {
    const _errs29 = errors;
    const _errs30 = errors;
    if (errors === _errs30) {
      if (data && typeof data == "object" && !Array.isArray(data)) {
        let missing1;
        if (
          (data.type === undefined && (missing1 = "type")) ||
          (data.conversation_id === undefined &&
            (missing1 = "conversation_id")) ||
          (data.run_id === undefined && (missing1 = "run_id")) ||
          (data.control_epoch === undefined && (missing1 = "control_epoch")) ||
          (data.attempt === undefined && (missing1 = "attempt")) ||
          (data.chunk_index === undefined && (missing1 = "chunk_index")) ||
          (data.text === undefined && (missing1 = "text"))
        ) {
          const err17 = {
            instancePath,
            schemaPath: "#/$defs/AiDelta/required",
            keyword: "required",
            params: { missingProperty: missing1 },
            message: "must have required property '" + missing1 + "'",
          };
          if (vErrors === null) {
            vErrors = [err17];
          } else {
            vErrors.push(err17);
          }
          errors++;
        } else {
          if (data.attempt !== undefined) {
            let data8 = data.attempt;
            const _errs32 = errors;
            if (!(typeof data8 == "number" && !(data8 % 1) && !isNaN(data8))) {
              const err18 = {
                instancePath: instancePath + "/attempt",
                schemaPath: "#/$defs/AiDelta/properties/attempt/type",
                keyword: "type",
                params: { type: "integer" },
                message: "must be integer",
              };
              if (vErrors === null) {
                vErrors = [err18];
              } else {
                vErrors.push(err18);
              }
              errors++;
            }
            if (errors === _errs32) {
              if (typeof data8 == "number") {
                if (data8 > 3 || isNaN(data8)) {
                  const err19 = {
                    instancePath: instancePath + "/attempt",
                    schemaPath: "#/$defs/AiDelta/properties/attempt/maximum",
                    keyword: "maximum",
                    params: { comparison: "<=", limit: 3 },
                    message: "must be <= 3",
                  };
                  if (vErrors === null) {
                    vErrors = [err19];
                  } else {
                    vErrors.push(err19);
                  }
                  errors++;
                } else {
                  if (data8 < 1 || isNaN(data8)) {
                    const err20 = {
                      instancePath: instancePath + "/attempt",
                      schemaPath: "#/$defs/AiDelta/properties/attempt/minimum",
                      keyword: "minimum",
                      params: { comparison: ">=", limit: 1 },
                      message: "must be >= 1",
                    };
                    if (vErrors === null) {
                      vErrors = [err20];
                    } else {
                      vErrors.push(err20);
                    }
                    errors++;
                  }
                }
              }
            }
            var valid6 = _errs32 === errors;
          } else {
            var valid6 = true;
          }
          if (valid6) {
            if (data.chunk_index !== undefined) {
              let data9 = data.chunk_index;
              const _errs34 = errors;
              if (!(
                typeof data9 == "number" &&
                !(data9 % 1) &&
                !isNaN(data9)
              )) {
                const err21 = {
                  instancePath: instancePath + "/chunk_index",
                  schemaPath: "#/$defs/AiDelta/properties/chunk_index/type",
                  keyword: "type",
                  params: { type: "integer" },
                  message: "must be integer",
                };
                if (vErrors === null) {
                  vErrors = [err21];
                } else {
                  vErrors.push(err21);
                }
                errors++;
              }
              if (errors === _errs34) {
                if (typeof data9 == "number") {
                  if (data9 < 0 || isNaN(data9)) {
                    const err22 = {
                      instancePath: instancePath + "/chunk_index",
                      schemaPath:
                        "#/$defs/AiDelta/properties/chunk_index/minimum",
                      keyword: "minimum",
                      params: { comparison: ">=", limit: 0 },
                      message: "must be >= 0",
                    };
                    if (vErrors === null) {
                      vErrors = [err22];
                    } else {
                      vErrors.push(err22);
                    }
                    errors++;
                  }
                }
              }
              var valid6 = _errs34 === errors;
            } else {
              var valid6 = true;
            }
            if (valid6) {
              if (data.control_epoch !== undefined) {
                let data10 = data.control_epoch;
                const _errs36 = errors;
                if (!(
                  typeof data10 == "number" &&
                  !(data10 % 1) &&
                  !isNaN(data10)
                )) {
                  const err23 = {
                    instancePath: instancePath + "/control_epoch",
                    schemaPath: "#/$defs/AiDelta/properties/control_epoch/type",
                    keyword: "type",
                    params: { type: "integer" },
                    message: "must be integer",
                  };
                  if (vErrors === null) {
                    vErrors = [err23];
                  } else {
                    vErrors.push(err23);
                  }
                  errors++;
                }
                if (errors === _errs36) {
                  if (typeof data10 == "number") {
                    if (data10 < 0 || isNaN(data10)) {
                      const err24 = {
                        instancePath: instancePath + "/control_epoch",
                        schemaPath:
                          "#/$defs/AiDelta/properties/control_epoch/minimum",
                        keyword: "minimum",
                        params: { comparison: ">=", limit: 0 },
                        message: "must be >= 0",
                      };
                      if (vErrors === null) {
                        vErrors = [err24];
                      } else {
                        vErrors.push(err24);
                      }
                      errors++;
                    }
                  }
                }
                var valid6 = _errs36 === errors;
              } else {
                var valid6 = true;
              }
              if (valid6) {
                if (data.conversation_id !== undefined) {
                  const _errs38 = errors;
                  if (errors === _errs38) {
                    if (errors === _errs38) {
                      if (!(typeof data.conversation_id === "string")) {
                        const err25 = {
                          instancePath: instancePath + "/conversation_id",
                          schemaPath:
                            "#/$defs/AiDelta/properties/conversation_id/type",
                          keyword: "type",
                          params: { type: "string" },
                          message: "must be string",
                        };
                        if (vErrors === null) {
                          vErrors = [err25];
                        } else {
                          vErrors.push(err25);
                        }
                        errors++;
                      }
                    }
                  }
                  var valid6 = _errs38 === errors;
                } else {
                  var valid6 = true;
                }
                if (valid6) {
                  if (data.protocol_version !== undefined) {
                    let data12 = data.protocol_version;
                    const _errs40 = errors;
                    if (!(
                      typeof data12 == "number" &&
                      !(data12 % 1) &&
                      !isNaN(data12)
                    )) {
                      const err26 = {
                        instancePath: instancePath + "/protocol_version",
                        schemaPath:
                          "#/$defs/AiDelta/properties/protocol_version/type",
                        keyword: "type",
                        params: { type: "integer" },
                        message: "must be integer",
                      };
                      if (vErrors === null) {
                        vErrors = [err26];
                      } else {
                        vErrors.push(err26);
                      }
                      errors++;
                    }
                    if (1 !== data12) {
                      const err27 = {
                        instancePath: instancePath + "/protocol_version",
                        schemaPath:
                          "#/$defs/AiDelta/properties/protocol_version/const",
                        keyword: "const",
                        params: { allowedValue: 1 },
                        message: "must be equal to constant",
                      };
                      if (vErrors === null) {
                        vErrors = [err27];
                      } else {
                        vErrors.push(err27);
                      }
                      errors++;
                    }
                    var valid6 = _errs40 === errors;
                  } else {
                    var valid6 = true;
                  }
                  if (valid6) {
                    if (data.run_id !== undefined) {
                      const _errs42 = errors;
                      if (errors === _errs42) {
                        if (errors === _errs42) {
                          if (!(typeof data.run_id === "string")) {
                            const err28 = {
                              instancePath: instancePath + "/run_id",
                              schemaPath:
                                "#/$defs/AiDelta/properties/run_id/type",
                              keyword: "type",
                              params: { type: "string" },
                              message: "must be string",
                            };
                            if (vErrors === null) {
                              vErrors = [err28];
                            } else {
                              vErrors.push(err28);
                            }
                            errors++;
                          }
                        }
                      }
                      var valid6 = _errs42 === errors;
                    } else {
                      var valid6 = true;
                    }
                    if (valid6) {
                      if (data.text !== undefined) {
                        let data14 = data.text;
                        const _errs44 = errors;
                        if (errors === _errs44) {
                          if (typeof data14 === "string") {
                            if (func2(data14) > 8000) {
                              const err29 = {
                                instancePath: instancePath + "/text",
                                schemaPath:
                                  "#/$defs/AiDelta/properties/text/maxLength",
                                keyword: "maxLength",
                                params: { limit: 8000 },
                                message:
                                  "must NOT have more than 8000 characters",
                              };
                              if (vErrors === null) {
                                vErrors = [err29];
                              } else {
                                vErrors.push(err29);
                              }
                              errors++;
                            }
                          } else {
                            const err30 = {
                              instancePath: instancePath + "/text",
                              schemaPath:
                                "#/$defs/AiDelta/properties/text/type",
                              keyword: "type",
                              params: { type: "string" },
                              message: "must be string",
                            };
                            if (vErrors === null) {
                              vErrors = [err30];
                            } else {
                              vErrors.push(err30);
                            }
                            errors++;
                          }
                        }
                        var valid6 = _errs44 === errors;
                      } else {
                        var valid6 = true;
                      }
                      if (valid6) {
                        if (data.type !== undefined) {
                          let data15 = data.type;
                          const _errs46 = errors;
                          if (typeof data15 !== "string") {
                            const err31 = {
                              instancePath: instancePath + "/type",
                              schemaPath:
                                "#/$defs/AiDelta/properties/type/type",
                              keyword: "type",
                              params: { type: "string" },
                              message: "must be string",
                            };
                            if (vErrors === null) {
                              vErrors = [err31];
                            } else {
                              vErrors.push(err31);
                            }
                            errors++;
                          }
                          if ("ai.delta" !== data15) {
                            const err32 = {
                              instancePath: instancePath + "/type",
                              schemaPath:
                                "#/$defs/AiDelta/properties/type/const",
                              keyword: "const",
                              params: { allowedValue: "ai.delta" },
                              message: "must be equal to constant",
                            };
                            if (vErrors === null) {
                              vErrors = [err32];
                            } else {
                              vErrors.push(err32);
                            }
                            errors++;
                          }
                          var valid6 = _errs46 === errors;
                        } else {
                          var valid6 = true;
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      } else {
        const err33 = {
          instancePath,
          schemaPath: "#/$defs/AiDelta/type",
          keyword: "type",
          params: { type: "object" },
          message: "must be object",
        };
        if (vErrors === null) {
          vErrors = [err33];
        } else {
          vErrors.push(err33);
        }
        errors++;
      }
    }
    var _valid0 = _errs29 === errors;
    valid0 = valid0 || _valid0;
    if (!valid0) {
      const _errs48 = errors;
      const _errs49 = errors;
      if (errors === _errs49) {
        if (data && typeof data == "object" && !Array.isArray(data)) {
          let missing2;
          if (
            (data.type === undefined && (missing2 = "type")) ||
            (data.conversation_id === undefined &&
              (missing2 = "conversation_id")) ||
            (data.actor_id === undefined && (missing2 = "actor_id"))
          ) {
            const err34 = {
              instancePath,
              schemaPath: "#/$defs/TypingUpdate/required",
              keyword: "required",
              params: { missingProperty: missing2 },
              message: "must have required property '" + missing2 + "'",
            };
            if (vErrors === null) {
              vErrors = [err34];
            } else {
              vErrors.push(err34);
            }
            errors++;
          } else {
            if (data.actor_id !== undefined) {
              const _errs51 = errors;
              if (errors === _errs51) {
                if (errors === _errs51) {
                  if (!(typeof data.actor_id === "string")) {
                    const err35 = {
                      instancePath: instancePath + "/actor_id",
                      schemaPath:
                        "#/$defs/TypingUpdate/properties/actor_id/type",
                      keyword: "type",
                      params: { type: "string" },
                      message: "must be string",
                    };
                    if (vErrors === null) {
                      vErrors = [err35];
                    } else {
                      vErrors.push(err35);
                    }
                    errors++;
                  }
                }
              }
              var valid8 = _errs51 === errors;
            } else {
              var valid8 = true;
            }
            if (valid8) {
              if (data.conversation_id !== undefined) {
                const _errs53 = errors;
                if (errors === _errs53) {
                  if (errors === _errs53) {
                    if (!(typeof data.conversation_id === "string")) {
                      const err36 = {
                        instancePath: instancePath + "/conversation_id",
                        schemaPath:
                          "#/$defs/TypingUpdate/properties/conversation_id/type",
                        keyword: "type",
                        params: { type: "string" },
                        message: "must be string",
                      };
                      if (vErrors === null) {
                        vErrors = [err36];
                      } else {
                        vErrors.push(err36);
                      }
                      errors++;
                    }
                  }
                }
                var valid8 = _errs53 === errors;
              } else {
                var valid8 = true;
              }
              if (valid8) {
                if (data.expires_in !== undefined) {
                  let data18 = data.expires_in;
                  const _errs55 = errors;
                  if (!(
                    typeof data18 == "number" &&
                    !(data18 % 1) &&
                    !isNaN(data18)
                  )) {
                    const err37 = {
                      instancePath: instancePath + "/expires_in",
                      schemaPath:
                        "#/$defs/TypingUpdate/properties/expires_in/type",
                      keyword: "type",
                      params: { type: "integer" },
                      message: "must be integer",
                    };
                    if (vErrors === null) {
                      vErrors = [err37];
                    } else {
                      vErrors.push(err37);
                    }
                    errors++;
                  }
                  if (5 !== data18) {
                    const err38 = {
                      instancePath: instancePath + "/expires_in",
                      schemaPath:
                        "#/$defs/TypingUpdate/properties/expires_in/const",
                      keyword: "const",
                      params: { allowedValue: 5 },
                      message: "must be equal to constant",
                    };
                    if (vErrors === null) {
                      vErrors = [err38];
                    } else {
                      vErrors.push(err38);
                    }
                    errors++;
                  }
                  var valid8 = _errs55 === errors;
                } else {
                  var valid8 = true;
                }
                if (valid8) {
                  if (data.protocol_version !== undefined) {
                    let data19 = data.protocol_version;
                    const _errs57 = errors;
                    if (!(
                      typeof data19 == "number" &&
                      !(data19 % 1) &&
                      !isNaN(data19)
                    )) {
                      const err39 = {
                        instancePath: instancePath + "/protocol_version",
                        schemaPath:
                          "#/$defs/TypingUpdate/properties/protocol_version/type",
                        keyword: "type",
                        params: { type: "integer" },
                        message: "must be integer",
                      };
                      if (vErrors === null) {
                        vErrors = [err39];
                      } else {
                        vErrors.push(err39);
                      }
                      errors++;
                    }
                    if (1 !== data19) {
                      const err40 = {
                        instancePath: instancePath + "/protocol_version",
                        schemaPath:
                          "#/$defs/TypingUpdate/properties/protocol_version/const",
                        keyword: "const",
                        params: { allowedValue: 1 },
                        message: "must be equal to constant",
                      };
                      if (vErrors === null) {
                        vErrors = [err40];
                      } else {
                        vErrors.push(err40);
                      }
                      errors++;
                    }
                    var valid8 = _errs57 === errors;
                  } else {
                    var valid8 = true;
                  }
                  if (valid8) {
                    if (data.type !== undefined) {
                      let data20 = data.type;
                      const _errs59 = errors;
                      if (typeof data20 !== "string") {
                        const err41 = {
                          instancePath: instancePath + "/type",
                          schemaPath:
                            "#/$defs/TypingUpdate/properties/type/type",
                          keyword: "type",
                          params: { type: "string" },
                          message: "must be string",
                        };
                        if (vErrors === null) {
                          vErrors = [err41];
                        } else {
                          vErrors.push(err41);
                        }
                        errors++;
                      }
                      if ("typing.updated" !== data20) {
                        const err42 = {
                          instancePath: instancePath + "/type",
                          schemaPath:
                            "#/$defs/TypingUpdate/properties/type/const",
                          keyword: "const",
                          params: { allowedValue: "typing.updated" },
                          message: "must be equal to constant",
                        };
                        if (vErrors === null) {
                          vErrors = [err42];
                        } else {
                          vErrors.push(err42);
                        }
                        errors++;
                      }
                      var valid8 = _errs59 === errors;
                    } else {
                      var valid8 = true;
                    }
                  }
                }
              }
            }
          }
        } else {
          const err43 = {
            instancePath,
            schemaPath: "#/$defs/TypingUpdate/type",
            keyword: "type",
            params: { type: "object" },
            message: "must be object",
          };
          if (vErrors === null) {
            vErrors = [err43];
          } else {
            vErrors.push(err43);
          }
          errors++;
        }
      }
      var _valid0 = _errs48 === errors;
      valid0 = valid0 || _valid0;
      if (!valid0) {
        const _errs61 = errors;
        const _errs62 = errors;
        if (errors === _errs62) {
          if (data && typeof data == "object" && !Array.isArray(data)) {
            let missing3;
            if (
              (data.type === undefined && (missing3 = "type")) ||
              (data.conversation_id === undefined &&
                (missing3 = "conversation_id")) ||
              (data.actor_id === undefined && (missing3 = "actor_id")) ||
              (data.online === undefined && (missing3 = "online"))
            ) {
              const err44 = {
                instancePath,
                schemaPath: "#/$defs/PresenceUpdate/required",
                keyword: "required",
                params: { missingProperty: missing3 },
                message: "must have required property '" + missing3 + "'",
              };
              if (vErrors === null) {
                vErrors = [err44];
              } else {
                vErrors.push(err44);
              }
              errors++;
            } else {
              if (data.actor_id !== undefined) {
                const _errs64 = errors;
                if (errors === _errs64) {
                  if (errors === _errs64) {
                    if (!(typeof data.actor_id === "string")) {
                      const err45 = {
                        instancePath: instancePath + "/actor_id",
                        schemaPath:
                          "#/$defs/PresenceUpdate/properties/actor_id/type",
                        keyword: "type",
                        params: { type: "string" },
                        message: "must be string",
                      };
                      if (vErrors === null) {
                        vErrors = [err45];
                      } else {
                        vErrors.push(err45);
                      }
                      errors++;
                    }
                  }
                }
                var valid10 = _errs64 === errors;
              } else {
                var valid10 = true;
              }
              if (valid10) {
                if (data.conversation_id !== undefined) {
                  const _errs66 = errors;
                  if (errors === _errs66) {
                    if (errors === _errs66) {
                      if (!(typeof data.conversation_id === "string")) {
                        const err46 = {
                          instancePath: instancePath + "/conversation_id",
                          schemaPath:
                            "#/$defs/PresenceUpdate/properties/conversation_id/type",
                          keyword: "type",
                          params: { type: "string" },
                          message: "must be string",
                        };
                        if (vErrors === null) {
                          vErrors = [err46];
                        } else {
                          vErrors.push(err46);
                        }
                        errors++;
                      }
                    }
                  }
                  var valid10 = _errs66 === errors;
                } else {
                  var valid10 = true;
                }
                if (valid10) {
                  if (data.online !== undefined) {
                    const _errs68 = errors;
                    if (typeof data.online !== "boolean") {
                      const err47 = {
                        instancePath: instancePath + "/online",
                        schemaPath:
                          "#/$defs/PresenceUpdate/properties/online/type",
                        keyword: "type",
                        params: { type: "boolean" },
                        message: "must be boolean",
                      };
                      if (vErrors === null) {
                        vErrors = [err47];
                      } else {
                        vErrors.push(err47);
                      }
                      errors++;
                    }
                    var valid10 = _errs68 === errors;
                  } else {
                    var valid10 = true;
                  }
                  if (valid10) {
                    if (data.protocol_version !== undefined) {
                      let data24 = data.protocol_version;
                      const _errs70 = errors;
                      if (!(
                        typeof data24 == "number" &&
                        !(data24 % 1) &&
                        !isNaN(data24)
                      )) {
                        const err48 = {
                          instancePath: instancePath + "/protocol_version",
                          schemaPath:
                            "#/$defs/PresenceUpdate/properties/protocol_version/type",
                          keyword: "type",
                          params: { type: "integer" },
                          message: "must be integer",
                        };
                        if (vErrors === null) {
                          vErrors = [err48];
                        } else {
                          vErrors.push(err48);
                        }
                        errors++;
                      }
                      if (1 !== data24) {
                        const err49 = {
                          instancePath: instancePath + "/protocol_version",
                          schemaPath:
                            "#/$defs/PresenceUpdate/properties/protocol_version/const",
                          keyword: "const",
                          params: { allowedValue: 1 },
                          message: "must be equal to constant",
                        };
                        if (vErrors === null) {
                          vErrors = [err49];
                        } else {
                          vErrors.push(err49);
                        }
                        errors++;
                      }
                      var valid10 = _errs70 === errors;
                    } else {
                      var valid10 = true;
                    }
                    if (valid10) {
                      if (data.type !== undefined) {
                        let data25 = data.type;
                        const _errs72 = errors;
                        if (typeof data25 !== "string") {
                          const err50 = {
                            instancePath: instancePath + "/type",
                            schemaPath:
                              "#/$defs/PresenceUpdate/properties/type/type",
                            keyword: "type",
                            params: { type: "string" },
                            message: "must be string",
                          };
                          if (vErrors === null) {
                            vErrors = [err50];
                          } else {
                            vErrors.push(err50);
                          }
                          errors++;
                        }
                        if ("presence.updated" !== data25) {
                          const err51 = {
                            instancePath: instancePath + "/type",
                            schemaPath:
                              "#/$defs/PresenceUpdate/properties/type/const",
                            keyword: "const",
                            params: { allowedValue: "presence.updated" },
                            message: "must be equal to constant",
                          };
                          if (vErrors === null) {
                            vErrors = [err51];
                          } else {
                            vErrors.push(err51);
                          }
                          errors++;
                        }
                        var valid10 = _errs72 === errors;
                      } else {
                        var valid10 = true;
                      }
                    }
                  }
                }
              }
            }
          } else {
            const err52 = {
              instancePath,
              schemaPath: "#/$defs/PresenceUpdate/type",
              keyword: "type",
              params: { type: "object" },
              message: "must be object",
            };
            if (vErrors === null) {
              vErrors = [err52];
            } else {
              vErrors.push(err52);
            }
            errors++;
          }
        }
        var _valid0 = _errs61 === errors;
        valid0 = valid0 || _valid0;
      }
    }
  }
  if (!valid0) {
    const err53 = {
      instancePath,
      schemaPath: "#/anyOf",
      keyword: "anyOf",
      params: {},
      message: "must match a schema in anyOf",
    };
    if (vErrors === null) {
      vErrors = [err53];
    } else {
      vErrors.push(err53);
    }
    errors++;
    validate10.errors = vErrors;
    return false;
  } else {
    errors = _errs0;
    if (vErrors !== null) {
      if (_errs0) {
        vErrors.length = _errs0;
      } else {
        vErrors = null;
      }
    }
  }
  validate10.errors = vErrors;
  return errors === 0;
}
